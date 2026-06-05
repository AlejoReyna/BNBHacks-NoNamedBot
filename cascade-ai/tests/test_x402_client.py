"""Tests for the TWAK-native x402 request flow."""

from __future__ import annotations

from typing import Any

from src.data.x402_client import DEFAULT_PAYMENT_ASSET, X402Client
from src.execution.twak_interface import TWAKInterface


ENDPOINT = "https://mcp.coinmarketcap.com/x402/mcp"


class FakeTWAK:
    """Payment stub that records TWAK-native x402 request calls."""

    def __init__(self, payload: dict[str, Any] | None = None, exc: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.payload = payload or {"result": {"ok": True}}
        self.exc = exc

    def request_x402(self, url: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"url": url, **kwargs})
        if self.exc:
            raise self.exc
        return self.payload


def test_request_with_x402_delegates_payment_and_fetch_to_twak() -> None:
    twak = FakeTWAK()
    client = X402Client(endpoint=ENDPOINT, twak_interface=twak)

    payload = client.request_with_x402(
        "POST",
        {"jsonrpc": "2.0"},
        {"MCP-Protocol-Version": "2024-11-05", "X-CMC-MCP-API-KEY": "secret"},
    )

    assert payload == {"result": {"ok": True}}
    assert twak.calls == [
        {
            "url": ENDPOINT,
            "method": "POST",
            "body": {"jsonrpc": "2.0"},
            "max_payment_atomic": "10000",
            "prefer_network": "base",
            "prefer_method": "eip3009",
            "prefer_asset": DEFAULT_PAYMENT_ASSET,
        }
    ]


def test_request_with_x402_returns_none_when_twak_fails() -> None:
    client = X402Client(endpoint=ENDPOINT, twak_interface=FakeTWAK(exc=RuntimeError("PASSWORD_MISSING")))

    assert client.request_with_x402("POST", {"a": 1}, {}) is None


def test_request_with_x402_requires_post() -> None:
    client = X402Client(endpoint=ENDPOINT, twak_interface=FakeTWAK())

    assert client.request_with_x402("GET", {"a": 1}, {}) is None


def test_x402_max_payment_converts_major_usdc_to_atomic_units() -> None:
    client = X402Client(default_amount="0.01", default_asset=DEFAULT_PAYMENT_ASSET)

    assert client._max_payment_atomic() == "10000"


def test_x402_max_payment_accepts_already_atomic_units() -> None:
    client = X402Client(default_amount="10000", default_asset=DEFAULT_PAYMENT_ASSET)

    assert client._max_payment_atomic() == "10000"


def test_twak_atomic_units_for_stables() -> None:
    assert TWAKInterface._amount_to_atomic_units(0.01, "USDC") == "10000"
    assert TWAKInterface._amount_to_atomic_units(0.01, DEFAULT_PAYMENT_ASSET) == "10000"
    assert TWAKInterface._amount_to_atomic_units(0.01, "BNB") == "10000000000000000"
