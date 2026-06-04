"""Tests for x402 payment retry behavior."""

from __future__ import annotations

import base64
import json
from typing import Any

import requests
import pytest

from src.data.x402_client import X402Client
from src.execution.twak_interface import TWAKInterface


TX_HASH = "0x" + "a" * 64
PAYMENT_SIGNATURE = "abc.def.ghi"


class FakeResponse:
    """Small response stub for requests.request monkeypatching."""

    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeTWAK:
    """Payment stub that records x402 calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, float, str]] = []

    def pay_x402(self, url: str, amount: float, asset: str) -> object:
        self.calls.append((url, amount, asset))
        return type(
            "Result",
            (),
            {
                "stdout": (
                    f'{{"payment_signature":"{PAYMENT_SIGNATURE}",'
                    f'"tx_hash":"{TX_HASH}","headers":{{"X-CUSTOM-PROOF":"bad"}}}}'
                )
            },
        )()


class FakeRequestTWAK:
    """x402 request stub for current TWAK CLI behavior."""

    def __init__(self, stdout: str = '{"result":{"ok":true}}', fail: bool = False) -> None:
        self.stdout = stdout
        self.fail = fail
        self.calls: list[tuple[str, str, dict[str, Any] | None, float, str]] = []

    def request_x402(
        self,
        url: str,
        method: str,
        json_body: dict[str, Any] | None,
        amount: float,
        asset: str,
    ) -> object:
        self.calls.append((url, method, json_body, amount, asset))
        if self.fail:
            raise RuntimeError("twak failed")
        return type("Result", (), {"stdout": self.stdout})()


def _payment_required_header(payload: dict[str, Any]) -> dict[str, str]:
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return {"payment-required": encoded}


def test_normal_200_response_returns_without_twak_payment(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request(**kwargs: Any) -> FakeResponse:
        calls.append(kwargs)
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: fake_request(**kwargs))
    twak = FakeTWAK()
    client = X402Client("https://mcp.coinmarketcap.com/x402/mcp", 0.01, "USDC", twak_interface=twak)

    response = client.request("POST", "https://example.test", json_body={"a": 1})

    assert response.status_code == 200
    assert twak.calls == []
    assert len(calls) == 1


def test_402_response_pays_and_retries_with_payment_proof_headers(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []
    challenge = {
        "resource": {"url": "https://mcp.coinmarketcap.com/x402/mcp"},
        "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "10000"}],
    }
    responses = [
        FakeResponse(
            402,
            {
                "payment": {
                    "amount": 0.01,
                    "asset": "USDC",
                }
            },
            headers=_payment_required_header(challenge),
        ),
        FakeResponse(200, {"ok": True}),
    ]

    def fake_request(*args: Any, **kwargs: Any) -> FakeResponse:
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(requests, "request", fake_request)
    twak = FakeTWAK()
    client = X402Client("https://mcp.coinmarketcap.com/x402/mcp", 0.01, "USDC", twak_interface=twak)

    response = client.request("POST", "https://example.test", headers={"X-BASE": "1"})

    assert response.status_code == 200
    assert twak.calls == [("https://mcp.coinmarketcap.com/x402/mcp", 0.01, "USDC")]
    retry_headers = calls[1]["headers"]
    assert retry_headers["X-BASE"] == "1"
    assert retry_headers["PAYMENT-SIGNATURE"] == PAYMENT_SIGNATURE
    assert "X-TWAK-TX-HASH" not in retry_headers
    assert "X-CUSTOM-PROOF" not in retry_headers


def test_current_twak_request_flow_returns_paid_endpoint_content(monkeypatch: Any) -> None:
    responses = [
        FakeResponse(
            402,
            {"payment": {"amount": 0.01, "asset": "USDC"}},
            headers=_payment_required_header({"resource": {"url": "https://mcp.coinmarketcap.com/x402/mcp"}}),
        )
    ]

    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: responses.pop(0))
    twak = FakeRequestTWAK()
    client = X402Client("https://mcp.coinmarketcap.com/x402/mcp", 0.01, "USDC", twak_interface=twak)  # type: ignore[arg-type]

    response = client.request("POST", "https://example.test", json_body={"a": 1})

    assert response.status_code == 200
    assert response.json() == {"result": {"ok": True}}
    assert twak.calls == [("https://mcp.coinmarketcap.com/x402/mcp", "POST", {"a": 1}, 0.01, "USDC")]


def test_current_twak_request_failure_returns_unpaid_response(monkeypatch: Any) -> None:
    unpaid = FakeResponse(
        402,
        {"payment": {"amount": 0.01, "asset": "USDC"}},
        headers=_payment_required_header({"resource": {"url": "https://mcp.coinmarketcap.com/x402/mcp"}}),
    )
    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: unpaid)
    client = X402Client(
        "https://mcp.coinmarketcap.com/x402/mcp",
        0.01,
        "USDC",
        twak_interface=FakeRequestTWAK(fail=True),  # type: ignore[arg-type]
    )

    response = client.request("POST", "https://example.test", json_body={"a": 1})

    assert response.status_code == 402


def test_non_url_cmc_resource_falls_back_to_configured_endpoint(monkeypatch: Any) -> None:
    responses = [
        FakeResponse(
            402,
            {"error": "Provide PAYMENT-SIGNATURE header to pay and retry."},
            headers=_payment_required_header({"resource": "X402_get_crypto_quotes_latest"}),
        ),
        FakeResponse(200, {"ok": True}),
    ]

    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: responses.pop(0))
    twak = FakeTWAK()
    client = X402Client("https://mcp.coinmarketcap.com/x402/mcp", 0.01, "USDC", twak_interface=twak)

    response = client.request("POST", "https://example.test")

    assert response.status_code == 200
    assert twak.calls == [("https://mcp.coinmarketcap.com/x402/mcp", 0.01, "USDC")]


def test_tx_hash_stdout_is_sanitized_as_fallback_payment_signature() -> None:
    headers = X402Client._proof_headers_from_stdout(f"paid {TX_HASH}")
    assert headers == {"PAYMENT-SIGNATURE": TX_HASH, "X-TWAK-TX-HASH": TX_HASH}


def test_402_rejects_non_whitelisted_payment_url(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: FakeResponse(
            402,
            {"payment": {"url": "https://evil.example/pay", "amount": 0.01, "asset": "USDC"}},
        ),
    )
    client = X402Client("https://mcp.coinmarketcap.com/x402/mcp", 0.01, "USDC", twak_interface=FakeTWAK())

    with pytest.raises(ValueError):
        client.request("POST", "https://example.test")


def test_twak_atomic_units_for_stables() -> None:
    assert TWAKInterface._amount_to_atomic_units(0.01, "USDC") == "10000"
    assert TWAKInterface._amount_to_atomic_units(0.01, "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913") == "10000"
    assert TWAKInterface._amount_to_atomic_units(0.01, "BNB") == "10000000000000000"
