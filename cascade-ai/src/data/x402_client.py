"""CoinMarketCap x402 client that delegates payment and signing to TWAK."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from src.execution.twak_interface import TWAKInterface

LOGGER = logging.getLogger(__name__)

CMC_X402_ENDPOINT = "https://mcp.coinmarketcap.com/x402/mcp"
DEFAULT_PAYMENT_ASSET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
DEFAULT_PAYMENT_CHAIN = "base"
DEFAULT_PAYMENT_METHOD = "eip3009"
DEFAULT_MAX_PAYMENT_USDC = "0.01"


class X402Client:
    """Run CMC x402 requests through TWAK native local signing.

    TWAK owns the HTTP request when using `twak x402 request`; this is the
    prize-aligned path because the user's TWAK wallet signs the x402
    authorization locally. Callers keep Keyless fallback for CMC header or
    endpoint incompatibilities.
    """

    def __init__(
        self,
        endpoint: str = CMC_X402_ENDPOINT,
        timeout_seconds: float = 15.0,
        twak_interface: TWAKInterface | None = None,
        default_amount: str | None = None,
        default_asset: str = DEFAULT_PAYMENT_ASSET,
        default_chain: str = DEFAULT_PAYMENT_CHAIN,
        default_method: str = DEFAULT_PAYMENT_METHOD,
    ) -> None:
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.twak_interface = twak_interface or TWAKInterface()
        self.default_amount = default_amount or DEFAULT_MAX_PAYMENT_USDC
        self.default_asset = default_asset
        self.default_chain = default_chain
        self.default_method = default_method

    def request_with_x402(self, method: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any] | None:
        """Ask TWAK to pay and fetch an x402-gated CMC MCP request."""

        try:
            if method.upper() != "POST":
                raise ValueError("CMC MCP x402 client only supports POST requests")
            if headers:
                LOGGER.debug(
                    "TWAK x402 request owns HTTP headers; %d caller header(s) are kept for fallback clients only",
                    len(headers),
                )
            return self.twak_interface.request_x402(
                self.endpoint,
                method="POST",
                body=payload,
                max_payment_atomic=self._max_payment_atomic(),
                prefer_network=self.default_chain,
                prefer_method=self.default_method,
                prefer_asset=self.default_asset,
            )
        except Exception as exc:
            LOGGER.warning("TWAK x402 request failed: %s", exc)
            return None

    def _max_payment_atomic(self) -> str:
        """Return TWAK's --max-payment value in atomic token units."""

        amount_text = str(self.default_amount or DEFAULT_MAX_PAYMENT_USDC).strip()
        if amount_text.isdigit():
            return amount_text
        try:
            amount = Decimal(amount_text)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"invalid CMC x402 payment amount: {self.default_amount!r}") from exc
        if amount <= 0:
            raise ValueError("CMC x402 payment amount must be greater than zero")
        decimals = 6 if _is_six_decimal_asset(self.default_asset) else 18
        return str(int(amount * (Decimal(10) ** decimals)))


def _is_six_decimal_asset(asset: str) -> bool:
    normalized = asset.strip().lower()
    return normalized in {
        "usdc",
        "usdt",
        DEFAULT_PAYMENT_ASSET.lower(),
    }
