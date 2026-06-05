"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


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
    cmc_mcp_enabled: bool = False
    cmc_mcp_shadow_mode: bool = True
    cmc_mcp_url: str = "https://mcp.coinmarketcap.com/x402/mcp"
    # Do not add CMC_X402_EPHEMERAL_KEY here. Settings is passed into execution
    # objects, and x402 data micropayment keys must stay isolated in src.data.
    cmc_x402_chain_id: int = 8453
    cmc_x402_max_usdc_per_call: float = 0.01
    use_keyless_primary: bool = True
    cmc_keyless_base_url: str = "https://pro-api.coinmarketcap.com/trial-pro-api/v3"
    paper_trade: bool = True
    loop_seconds: int = 300
    max_position_pct: float = 0.05
    max_daily_trades: int = 3
    max_daily_loss_pct: float = 0.03
    max_slippage_pct: float = 0.01
    drawdown_kill_switch_pct: float = 0.20
    trailing_stop_pct: float = 0.035
    take_profit_pct: float = 0.08
    # One-week competition window: require BNB to be only mildly weak at worst
    # so entries are not opened into broad-market rollovers that increase drawdown.
    bnb_regime_threshold: float = -0.01
    # One-week competition window: token must already be flat-to-positive on 1h
    # while avoiding severe 24h downtrends; these are fail-closed drawdown guards.
    token_regime_1h_min: float = 0.0025
    token_regime_24h_min: float = -0.08
    # One-week competition window: 3h highs catch breakouts earlier, while the
    # 0.2% buffer avoids chasing tiny noisy ticks that can inflate drawdown.
    breakout_lookback_hours: int = 3
    breakout_buffer: float = 0.002
    # Minimum passing count across the four core entry factors; slippage remains mandatory.
    min_entry_factors: int = Field(default=4, ge=1, le=4)
    log_level: str = "INFO"
    demo_mode: bool = False
    position_state_path: str = "positions.json"
    guardrail_state_path: str = "guardrail_state.json"
    execution_log_path: str = "execution_log.jsonl"
    decision_log_path: str = "decision_log.jsonl"


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
        "cmc_mcp_enabled": _get_bool("CMC_MCP_ENABLED", False),
        "cmc_mcp_shadow_mode": _get_bool("CMC_MCP_SHADOW_MODE", True),
        "cmc_mcp_url": os.getenv(
            "CMC_MCP_URL",
            os.getenv("CMC_X402_ENDPOINT", "https://mcp.coinmarketcap.com/x402/mcp"),
        ),
        "cmc_x402_chain_id": _get_int("CMC_X402_CHAIN_ID", 8453),
        "cmc_x402_max_usdc_per_call": _get_float("CMC_X402_MAX_USDC_PER_CALL", 0.01),
        "use_keyless_primary": _get_bool("USE_KEYLESS_PRIMARY", True),
        "cmc_keyless_base_url": os.getenv(
            "CMC_KEYLESS_BASE_URL",
            "https://pro-api.coinmarketcap.com/trial-pro-api/v3",
        ),
        "paper_trade": _get_bool("PAPER_TRADE", True),
        "loop_seconds": _get_int("LOOP_SECONDS", 300),
        "max_position_pct": _get_float("MAX_POSITION_PCT", 0.05),
        "max_daily_trades": _get_int("MAX_DAILY_TRADES", 3),
        "max_daily_loss_pct": _get_float("MAX_DAILY_LOSS_PCT", 0.03),
        "max_slippage_pct": _get_float("MAX_SLIPPAGE_PCT", 0.01),
        "drawdown_kill_switch_pct": _get_float("DRAWDOWN_KILL_SWITCH_PCT", 0.20),
        "trailing_stop_pct": _get_float("TRAILING_STOP_PCT", 0.035),
        "take_profit_pct": _get_float("TAKE_PROFIT_PCT", 0.08),
        "bnb_regime_threshold": _get_float("BNB_REGIME_THRESHOLD", -0.01),
        "token_regime_1h_min": _get_float("TOKEN_REGIME_1H_MIN", 0.0025),
        "token_regime_24h_min": _get_float("TOKEN_REGIME_24H_MIN", -0.08),
        "breakout_lookback_hours": _get_int("BREAKOUT_LOOKBACK_HOURS", 3),
        "breakout_buffer": _get_float("BREAKOUT_BUFFER", 0.002),
        "min_entry_factors": _get_int("MIN_ENTRY_FACTORS", 4),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "demo_mode": _get_bool("DEMO_MODE", False),
        "position_state_path": os.getenv("POSITION_STATE_PATH", "positions.json"),
        "guardrail_state_path": os.getenv("GUARDRAIL_STATE_PATH", "guardrail_state.json"),
        "execution_log_path": os.getenv("EXECUTION_LOG_PATH", "execution_log.jsonl"),
        "decision_log_path": os.getenv("DECISION_LOG_PATH", "decision_log.jsonl"),
    }
    return Settings(**values)
