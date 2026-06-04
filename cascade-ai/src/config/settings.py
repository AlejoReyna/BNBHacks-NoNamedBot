"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    """Runtime settings for the trading agent."""

    cmc_api_key: Optional[str] = None
    bsc_rpc_url: Optional[str] = None
    base_rpc_url: Optional[str] = None
    opbnb_provider_url: Optional[str] = "https://opbnb-mainnet-rpc.bnbchain.org"
    wallet_address: Optional[str] = None
    usdc_token_address: Optional[str] = None
    default_stable_symbol: str = "USDC"
    cmc_x402_endpoint: str = "https://mcp.coinmarketcap.com/x402/mcp"
    cmc_x402_amount: float = 0.01
    cmc_x402_asset: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    paper_trade: bool = True
    loop_seconds: int = 300
    max_position_pct: float = 0.05
    max_daily_trades: int = 3
    max_daily_loss_pct: float = 0.03
    max_slippage_pct: float = 0.01
    drawdown_kill_switch_pct: float = 0.20
    trailing_stop_pct: float = 0.035
    take_profit_pct: float = 0.08
    min_entry_factors: int = 4
    log_level: str = "INFO"
    position_state_path: str = "positions.json"
    guardrail_state_path: str = "guardrail_state.json"


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _none_if_blank(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    return value


def load_settings(dotenv_path: str | None = None) -> Settings:
    """Load settings from .env and the current process environment."""

    load_dotenv(dotenv_path=dotenv_path)
    values: dict[str, Any] = {
        "cmc_api_key": _none_if_blank(os.getenv("CMC_API_KEY")),
        "bsc_rpc_url": _none_if_blank(os.getenv("BSC_RPC_URL") or os.getenv("BSC_PROVIDER_URL")),
        "base_rpc_url": _none_if_blank(os.getenv("BASE_RPC_URL")),
        "opbnb_provider_url": _none_if_blank(os.getenv("OPBNB_PROVIDER_URL"))
        or "https://opbnb-mainnet-rpc.bnbchain.org",
        "wallet_address": _none_if_blank(os.getenv("WALLET_ADDRESS") or os.getenv("AGENT_WALLET_ADDRESS")),
        "usdc_token_address": _none_if_blank(os.getenv("USDC_TOKEN_ADDRESS")),
        "default_stable_symbol": os.getenv("DEFAULT_STABLE_SYMBOL", "USDC"),
        "cmc_x402_endpoint": os.getenv(
            "CMC_X402_ENDPOINT",
            "https://mcp.coinmarketcap.com/x402/mcp",
        ),
        "cmc_x402_amount": _get_float("CMC_X402_AMOUNT", 0.01),
        "cmc_x402_asset": os.getenv("CMC_X402_ASSET", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
        "paper_trade": _get_bool("PAPER_TRADE", True),
        "loop_seconds": _get_int("LOOP_SECONDS", 300),
        "max_position_pct": _get_float("MAX_POSITION_PCT", 0.05),
        "max_daily_trades": _get_int("MAX_DAILY_TRADES", 3),
        "max_daily_loss_pct": _get_float("MAX_DAILY_LOSS_PCT", 0.03),
        "max_slippage_pct": _get_float("MAX_SLIPPAGE_PCT", 0.01),
        "drawdown_kill_switch_pct": _get_float("DRAWDOWN_KILL_SWITCH_PCT", 0.20),
        "trailing_stop_pct": _get_float("TRAILING_STOP_PCT", 0.035),
        "take_profit_pct": _get_float("TAKE_PROFIT_PCT", 0.08),
        "min_entry_factors": _get_int("MIN_ENTRY_FACTORS", 4),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "position_state_path": os.getenv("POSITION_STATE_PATH", "positions.json"),
        "guardrail_state_path": os.getenv("GUARDRAIL_STATE_PATH", "guardrail_state.json"),
    }
    return Settings(**values)
