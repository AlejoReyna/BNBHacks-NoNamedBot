"""Tests for CoinMarketCap MCP request envelopes."""

from __future__ import annotations

from typing import Any

from src.config.settings import Settings
from src.data.cmc_mcp_client import CMCMCPClient


class FakeResponse:
    """Minimal response object for CMCMCPClient tests."""

    status_code = 200

    def json(self) -> dict[str, Any]:
        return {"result": {"ok": True}}

    def raise_for_status(self) -> None:
        return None


class FakeX402Client:
    """Capture outgoing MCP request data."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        self.calls.append({"method": method, "url": url, "json_body": json_body, "headers": headers})
        return FakeResponse()


def test_cmc_mcp_uses_documented_api_key_header() -> None:
    fake_x402 = FakeX402Client()
    client = CMCMCPClient(Settings(cmc_api_key="secret"), x402_client=fake_x402)  # type: ignore[arg-type]

    result = client.get_crypto_quotes_latest(["CAKE"])

    assert result == {"ok": True}
    assert fake_x402.calls[0]["headers"]["X-CMC-MCP-API-KEY"] == "secret"
    assert "X-CMC_PRO_API_KEY" not in fake_x402.calls[0]["headers"]


def test_market_metrics_uses_documented_tool_name() -> None:
    fake_x402 = FakeX402Client()
    client = CMCMCPClient(Settings(), x402_client=fake_x402)  # type: ignore[arg-type]

    client.get_crypto_market_metrics(["CAKE"])

    params = fake_x402.calls[0]["json_body"]["params"]
    assert params["name"] == "get_crypto_market_metrics"


def test_market_snapshot_skips_remaining_calls_when_quotes_unavailable(monkeypatch: Any) -> None:
    client = CMCMCPClient(Settings(), x402_client=FakeX402Client())  # type: ignore[arg-type]
    called: list[str] = []

    monkeypatch.setattr(client, "get_crypto_quotes_latest", lambda symbols: {})
    monkeypatch.setattr(client, "get_crypto_technical_analysis", lambda symbols: called.append("technicals"))
    monkeypatch.setattr(client, "get_global_crypto_derivatives_metrics", lambda: called.append("derivatives"))
    monkeypatch.setattr(client, "get_crypto_market_metrics", lambda symbols: called.append("metrics"))

    assert client.fetch_market_snapshot(["CAKE"]) == {}
    assert called == []
