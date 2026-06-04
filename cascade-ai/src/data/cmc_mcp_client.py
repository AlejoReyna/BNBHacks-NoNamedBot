"""CoinMarketCap MCP client using the verified CMC tool names."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import requests

from src.config.settings import Settings
from src.config.tokens import TARGET_20_SYMBOLS, get_cmc_id
from src.data.x402_client import X402Client

LOGGER = logging.getLogger(__name__)


class CMCMCPClient:
    """Small JSON-RPC/MCP client for CoinMarketCap AI Agent Hub data."""

    def __init__(self, settings: Settings, x402_client: X402Client | None = None) -> None:
        self.settings = settings
        self.endpoint = settings.cmc_x402_endpoint
        self.x402_client = x402_client or X402Client(
            endpoint=settings.cmc_x402_endpoint,
            amount=settings.cmc_x402_amount,
            asset=settings.cmc_x402_asset,
        )

    def get_crypto_quotes_latest(self, symbols: list[str]) -> dict[str, Any]:
        """Call CMC MCP get_crypto_quotes_latest."""

        return self._call_tool("get_crypto_quotes_latest", {"id": self._symbols_to_id_arg(symbols)})

    def get_crypto_technical_analysis(self, symbols: list[str]) -> dict[str, Any]:
        """Call CMC MCP get_crypto_technical_analysis."""

        return self._call_tool("get_crypto_technical_analysis", {"id": self._symbols_to_id_arg(symbols)})

    def get_global_crypto_derivatives_metrics(self) -> dict[str, Any]:
        """Call CMC MCP get_global_crypto_derivatives_metrics."""

        return self._call_tool("get_global_crypto_derivatives_metrics", {})

    def get_crypto_market_metrics(self, symbols: list[str]) -> dict[str, Any]:
        """Call CMC MCP get_crypto_market_metrics."""

        return self._call_tool("get_crypto_market_metrics", {"id": self._symbols_to_id_arg(symbols)})

    def fetch_market_snapshot(self, symbols: list[str]) -> dict[str, Any]:
        """Fetch and normalize the combined market snapshot for strategy evaluation."""

        normalized_symbols = [symbol.upper() for symbol in symbols if symbol.upper() in TARGET_20_SYMBOLS]
        quotes = self.get_crypto_quotes_latest(normalized_symbols)
        if not quotes:
            LOGGER.warning("CMC quotes unavailable; skipping remaining market snapshot calls")
            return {}

        technicals = self.get_crypto_technical_analysis(normalized_symbols)
        derivatives = self.get_global_crypto_derivatives_metrics()
        market_metrics = self.get_crypto_market_metrics(normalized_symbols)

        quotes_by_symbol = self._by_symbol(quotes)
        technicals_by_symbol = self._by_symbol(technicals)
        metrics_by_symbol = self._by_symbol(market_metrics)
        bnb_trend = self._first_number(
            quotes_by_symbol.get("BNB", quotes_by_symbol.get("WBNB", {})),
            ("bnb_1h_trend_pct", "percent_change_1h", "price_change_percentage_1h", "change_1h"),
        )

        snapshot: dict[str, Any] = {}
        for symbol in normalized_symbols:
            quote_data = quotes_by_symbol.get(symbol, {})
            technical_data = technicals_by_symbol.get(symbol, {})
            metric_data = metrics_by_symbol.get(symbol, {})
            combined = [quote_data, technical_data, metric_data, derivatives]
            volume_24h = self._first_number_from_many(combined, ("volume_24h", "volume_24h_usd"))
            snapshot[symbol] = {
                "symbol": symbol,
                "price": self._first_number_from_many(combined, ("price", "last_price", "quote.USD.price")),
                "volume_1h": self._first_number_from_many(combined, ("volume_1h", "volume_1h_usd")),
                "rolling_24h_hourly_volume_avg": self._first_number_from_many(
                    combined,
                    ("rolling_24h_hourly_volume_avg", "avg_hourly_volume_24h"),
                    default=volume_24h / 24 if volume_24h else None,
                ),
                "high_6h": self._first_number_from_many(combined, ("high_6h", "high_6h_price")),
                "bnb_1h_trend_pct": bnb_trend,
                "rsi": self._first_number_from_many(combined, ("rsi", "rsi_14", "technical.rsi")),
                "macd": self._first_number_from_many(combined, ("macd", "technical.macd")),
                "estimated_slippage_pct": self._first_number_from_many(
                    combined,
                    ("estimated_slippage_pct", "slippage_pct"),
                ),
                "funding_rate": self._first_number_from_many(
                    combined,
                    ("funding_rate", "avg_funding_rate", "funding"),
                ),
                "open_interest_change_pct": self._first_number_from_many(
                    combined,
                    ("open_interest_change_pct", "oi_change_pct", "open_interest_24h_change_pct"),
                ),
            }
        return snapshot

    def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        envelope = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2024-11-05",
        }
        if self.settings.cmc_api_key:
            headers["X-CMC-MCP-API-KEY"] = self.settings.cmc_api_key

        try:
            response = self.x402_client.request(
                "POST",
                self.endpoint,
                json_body=envelope,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            LOGGER.warning("CMC MCP call %s failed; using empty fallback: %s", tool_name, exc)
            return {}

        if not isinstance(payload, dict):
            LOGGER.warning("CMC MCP call %s returned non-dict JSON; using empty fallback", tool_name)
            return {}
        result = payload.get("result", payload)
        if isinstance(result, dict):
            return result
        LOGGER.warning("CMC MCP call %s returned an unexpected result shape; using empty fallback", tool_name)
        return {}

    @classmethod
    def _by_symbol(cls, payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        items = cls._extract_items(payload)
        by_symbol: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or item.get("base_symbol") or "").upper()
            if symbol:
                by_symbol[symbol] = item
        if not by_symbol and isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, dict):
                    symbol = str(value.get("symbol") or key).upper()
                    by_symbol[symbol] = value
        return by_symbol

    @classmethod
    def _extract_items(cls, payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []
        for key in ("data", "items", "results", "tokens", "quotes"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                return list(value.values())
        return []

    @classmethod
    def _first_number_from_many(
        cls,
        payloads: list[dict[str, Any]],
        keys: tuple[str, ...],
        default: float | None = None,
    ) -> float | None:
        for payload in payloads:
            value = cls._first_number(payload, keys, default=None)
            if value is not None:
                return value
        return default

    @classmethod
    def _first_number(
        cls,
        payload: dict[str, Any],
        keys: tuple[str, ...],
        default: float | None = None,
    ) -> float | None:
        for key in keys:
            found = cls._read_path(payload, key)
            if found is not None:
                try:
                    return float(found)
                except (TypeError, ValueError):
                    continue
        for key in keys:
            found = cls._recursive_lookup(payload, key.split(".")[-1])
            if found is not None:
                try:
                    return float(found)
                except (TypeError, ValueError):
                    continue
        return default

    @staticmethod
    def _read_path(payload: dict[str, Any], path: str) -> Any:
        current: Any = payload
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    @classmethod
    def _recursive_lookup(cls, payload: Any, key: str) -> Any:
        if isinstance(payload, dict):
            if key in payload:
                return payload[key]
            for value in payload.values():
                found = cls._recursive_lookup(value, key)
                if found is not None:
                    return found
        if isinstance(payload, list):
            for value in payload:
                found = cls._recursive_lookup(value, key)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _symbols_to_id_arg(symbols: list[str]) -> str:
        return ",".join(get_cmc_id(symbol) for symbol in symbols)
