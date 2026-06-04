"""Executable risk guardrails for Plan B+."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from src.config.settings import Settings
from src.config.tokens import assert_tradable_symbol


@dataclass(frozen=True)
class TradeRecord:
    """Recorded trade used for daily limits and realized PnL tracking."""

    symbol: str
    side: Literal["buy", "sell"]
    value_usdc: float
    realized_pnl_usdc: float
    timestamp: datetime


class Guardrails:
    """Enforce non-negotiable trading limits."""

    def __init__(self, settings: Settings, state_path: str | Path | None = None) -> None:
        self.settings = settings
        self.state_path = Path(state_path or settings.guardrail_state_path)
        self.trade_records: list[TradeRecord] = []
        self._daily_date = self._now().date()
        self._daily_trade_count = 0
        self._daily_realized_loss_usdc = 0.0
        self._paused_until: datetime | None = None
        self._all_time_high_usdc = 0.0
        self._kill_switch = False
        self._load_state()
        self._reset_daily_if_needed()

    def validate_new_trade(
        self,
        symbol: str,
        position_value_usdc: float,
        portfolio_value_usdc: float,
        estimated_slippage_pct: float,
    ) -> None:
        """Raise if a new trade violates the configured guardrails."""

        self._reset_daily_if_needed()
        assert_tradable_symbol(symbol)
        if self._kill_switch:
            raise RuntimeError("drawdown kill switch is active")
        if not self.can_open_new_trade():
            seconds = self.seconds_until_trading_resumes()
            raise RuntimeError(f"new trades are paused for {seconds} more seconds")
        max_position_value = portfolio_value_usdc * self.settings.max_position_pct
        if position_value_usdc > max_position_value:
            raise ValueError(
                f"position value {position_value_usdc:.2f} exceeds max {max_position_value:.2f}"
            )
        if estimated_slippage_pct <= 0:
            raise ValueError("estimated slippage must be greater than zero")
        if estimated_slippage_pct > self.settings.max_slippage_pct:
            raise ValueError(
                f"estimated slippage {estimated_slippage_pct:.4f} exceeds cap {self.settings.max_slippage_pct:.4f}"
            )
        max_loss = portfolio_value_usdc * self.settings.max_daily_loss_pct
        if self._daily_realized_loss_usdc >= max_loss and max_loss > 0:
            raise RuntimeError("daily realized loss limit has been reached")

    def record_trade(self, record: TradeRecord, portfolio_value_usdc: float) -> None:
        """Record a trade and update daily counters."""

        self._reset_daily_if_needed(record.timestamp)
        assert_tradable_symbol(record.symbol)
        self.trade_records.append(record)
        if record.side == "buy":
            self._daily_trade_count += 1
        if record.realized_pnl_usdc < 0:
            self._daily_realized_loss_usdc += abs(record.realized_pnl_usdc)
        max_loss = portfolio_value_usdc * self.settings.max_daily_loss_pct
        if self._daily_realized_loss_usdc >= max_loss and max_loss > 0:
            self._paused_until = self._now() + timedelta(hours=24)
        self._save_state()

    def can_open_new_trade(self) -> bool:
        """Return whether a new position may be opened now."""

        self._reset_daily_if_needed()
        if self._kill_switch:
            return False
        if self._paused_until is not None and self._paused_until > self._now():
            return False
        return self._daily_trade_count < self.settings.max_daily_trades

    def update_portfolio_value(self, portfolio_value_usdc: float) -> bool:
        """Update all-time high tracking and return whether the kill switch is active."""

        if portfolio_value_usdc <= 0:
            return self._kill_switch
        if portfolio_value_usdc > self._all_time_high_usdc:
            self._all_time_high_usdc = portfolio_value_usdc
            self._save_state()
        drawdown_trigger = self._all_time_high_usdc * (1 - self.settings.drawdown_kill_switch_pct)
        if self._all_time_high_usdc > 0 and portfolio_value_usdc <= drawdown_trigger:
            self._kill_switch = True
        return self._kill_switch

    def should_kill_switch(self) -> bool:
        """Return whether the drawdown kill switch has fired."""

        return self._kill_switch

    def seconds_until_trading_resumes(self) -> int:
        """Return seconds remaining in the daily-loss pause window."""

        if self._paused_until is None:
            return 0
        remaining = self._paused_until - self._now()
        return max(0, int(remaining.total_seconds()))

    def _reset_daily_if_needed(self, current_time: datetime | None = None) -> None:
        now = current_time or self._now()
        if now.date() == self._daily_date:
            return
        self._daily_date = now.date()
        self._daily_trade_count = 0
        self._daily_realized_loss_usdc = 0.0
        if self._paused_until is not None and self._paused_until <= now:
            self._paused_until = None
        self._save_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            self._save_state()
            return
        with self.state_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid guardrail state file: {self.state_path}")

        self._daily_trade_count = int(payload.get("daily_trade_count", 0))
        self._daily_realized_loss_usdc = float(payload.get("daily_realized_loss", 0.0))
        self._all_time_high_usdc = float(payload.get("portfolio_ath", 0.0))
        self._daily_date = self._date_from_state(payload.get("last_reset_date"))

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "daily_trade_count": self._daily_trade_count,
            "daily_realized_loss": self._daily_realized_loss_usdc,
            "portfolio_ath": self._all_time_high_usdc,
            "last_reset_date": self._daily_date.isoformat(),
        }
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def _date_from_state(self, raw_value: object) -> date:
        if raw_value is None:
            return self._now().date()
        try:
            return date.fromisoformat(str(raw_value))
        except ValueError as exc:
            raise ValueError(f"Invalid last_reset_date in {self.state_path}") from exc

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
