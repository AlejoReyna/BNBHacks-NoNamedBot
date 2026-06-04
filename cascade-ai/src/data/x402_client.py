"""Conservative x402 HTTP client backed by TWAK subprocess payments."""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

import requests

from src.execution.twak_interface import TWAKInterface

LOGGER = logging.getLogger(__name__)


class X402PaymentRequired(Exception):
    """Raised when a request still requires payment after a TWAK retry."""


class X402Client:
    """HTTP client that pays x402 invoices through TWAK when required."""

    ALLOWED_PAYMENT_DOMAIN_SUFFIXES = ("coinmarketcap.com", "base.org")
    TX_HASH_PATTERN = re.compile(r"0x[a-fA-F0-9]{64}")
    JWT_PATTERN = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")

    def __init__(
        self,
        endpoint: str,
        amount: float,
        asset: str,
        timeout_seconds: float = 30.0,
        twak_interface: TWAKInterface | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.amount = amount
        self.asset = asset
        self.timeout_seconds = timeout_seconds
        self.twak_interface = twak_interface or TWAKInterface()

    def request(
        self,
        method: str,
        url: str,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        """Send a request, pay on HTTP 402, and retry with payment proof headers."""

        request_headers = dict(headers or {})
        response = requests.request(
            method,
            url,
            json=json_body,
            headers=request_headers,
            timeout=self.timeout_seconds,
        )
        if response.status_code != 402:
            return response

        details = self._extract_payment_details(response)
        payment_url = self._resolve_payment_url(details, url)
        amount = float(details.get("amount") or self.amount)
        asset = str(details.get("asset") or self.asset)

        if hasattr(self.twak_interface, "request_x402"):
            try:
                result = self.twak_interface.request_x402(payment_url, method, json_body, amount, asset)
            except RuntimeError as exc:
                LOGGER.warning("TWAK x402 request failed; returning unpaid response: %s", exc)
                return response
            return self._response_from_twak_stdout(result.stdout, url)

        result = self.twak_interface.pay_x402(payment_url, amount, asset)

        retry_headers = {
            **request_headers,
            **self._proof_headers_from_stdout(result.stdout),
        }
        retry_response = requests.request(
            method,
            url,
            json=json_body,
            headers=retry_headers,
            timeout=self.timeout_seconds,
        )
        if retry_response.status_code == 402:
            raise X402PaymentRequired("x402 payment was attempted, but the endpoint still returned HTTP 402")
        return retry_response

    @staticmethod
    def _response_from_twak_stdout(stdout: str, url: str) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response.url = url
        response.headers["Content-Type"] = "application/json"
        payload = stdout.strip()
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            response._content = payload.encode("utf-8")
            return response
        response._content = json.dumps(parsed).encode("utf-8")
        return response

    @classmethod
    def _extract_payment_details(cls, response: requests.Response) -> dict[str, Any]:
        merged = cls._decode_payment_required_header(response)
        try:
            payload = response.json()
        except ValueError:
            return merged
        if not isinstance(payload, dict):
            return merged

        merged.update(payload)
        resource = payload.get("resource")
        if isinstance(resource, dict):
            resource_url = resource.get("url")
            if isinstance(resource_url, str):
                merged["resource_url"] = resource_url
        for key in ("payment", "payment_required", "x402", "error"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                merged.update(nested)
        return merged

    def _resolve_payment_url(self, details: dict[str, Any], request_url: str) -> str:
        for candidate in (
            details.get("url"),
            details.get("payment_url"),
            details.get("resource_url"),
            self.endpoint,
            request_url,
        ):
            if not isinstance(candidate, str) or not candidate.startswith("https://"):
                continue
            return self._validated_payment_url(candidate)
        raise ValueError("No valid x402 payment URL was provided by an official CMC/Base domain")

    @classmethod
    def _proof_headers_from_stdout(cls, stdout: str) -> dict[str, str]:
        proof = stdout.strip()
        if not proof:
            raise ValueError("TWAK did not return an x402 payment proof")

        payment_signature = cls._extract_payment_signature(proof)
        if payment_signature is not None:
            return {"PAYMENT-SIGNATURE": payment_signature}

        tx_hash = cls._extract_tx_hash(proof)
        if tx_hash is not None:
            return {
                "PAYMENT-SIGNATURE": tx_hash,
                "X-TWAK-TX-HASH": tx_hash,
            }
        raise ValueError("TWAK stdout did not contain a valid x402 payment proof")

    @classmethod
    def _decode_payment_required_header(cls, response: requests.Response) -> dict[str, Any]:
        header_value = cls._header_value(response, "payment-required")
        if not header_value:
            return {}
        try:
            decoded = base64.b64decode(cls._pad_base64(header_value)).decode("utf-8")
            payload = json.loads(decoded)
        except (ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        resource = payload.get("resource")
        if isinstance(resource, dict) and isinstance(resource.get("url"), str):
            payload["resource_url"] = resource["url"]
        return payload

    @staticmethod
    def _header_value(response: requests.Response, name: str) -> str | None:
        for key, value in response.headers.items():
            if key.lower() == name.lower():
                return value
        return None

    @staticmethod
    def _pad_base64(value: str) -> str:
        return value + "=" * (-len(value) % 4)

    @classmethod
    def _extract_payment_signature(cls, stdout: str) -> str | None:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout if cls.JWT_PATTERN.fullmatch(stdout) else None
        return cls._extract_payment_signature_from_json(payload)

    @classmethod
    def _extract_payment_signature_from_json(cls, payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key in ("payment_signature", "paymentSignature", "signature", "PAYMENT-SIGNATURE"):
                value = payload.get(key)
                if isinstance(value, str) and cls.JWT_PATTERN.fullmatch(value.strip()):
                    return value.strip()
            for value in payload.values():
                found = cls._extract_payment_signature_from_json(value)
                if found is not None:
                    return found
        if isinstance(payload, list):
            for value in payload:
                found = cls._extract_payment_signature_from_json(value)
                if found is not None:
                    return found
        return None

    @classmethod
    def _extract_tx_hash(cls, stdout: str) -> str | None:
        direct_match = cls.TX_HASH_PATTERN.search(stdout)
        if direct_match:
            return direct_match.group(0)

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return None

        return cls._extract_tx_hash_from_json(payload)

    @classmethod
    def _extract_tx_hash_from_json(cls, payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key in ("tx_hash", "txHash", "transaction_hash", "transactionHash", "hash"):
                value = payload.get(key)
                if isinstance(value, str) and cls.TX_HASH_PATTERN.fullmatch(value.strip()):
                    return value.strip()
            for value in payload.values():
                found = cls._extract_tx_hash_from_json(value)
                if found is not None:
                    return found
        if isinstance(payload, list):
            for value in payload:
                found = cls._extract_tx_hash_from_json(value)
                if found is not None:
                    return found
        return None

    @classmethod
    def _validated_payment_url(cls, payment_url: str) -> str:
        parsed = urlparse(payment_url)
        hostname = (parsed.hostname or "").lower()
        allowed = parsed.scheme == "https" and any(
            hostname == suffix or hostname.endswith("." + suffix)
            for suffix in cls.ALLOWED_PAYMENT_DOMAIN_SUFFIXES
        )
        if not allowed:
            raise ValueError(f"Refusing x402 payment URL outside official CMC/Base domains: {payment_url}")
        return payment_url
