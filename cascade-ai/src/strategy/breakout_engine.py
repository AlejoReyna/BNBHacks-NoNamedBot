"""Six-factor momentum breakout strategy engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config.settings import Settings
from src.config.tokens import is_tradable_symbol


@dataclass(frozen=True)
class BreakoutDecision:
    """Decision returned by the breakout engine."""

    should_enter: bool
    symbol: str | None
    position_size_usdc: float
    factor_scores: dict[str, bool]
    true_factor_count: int
    reason: str


class BreakoutEngine:
    """Evaluate BSC tokens against the Plan B+ entry filter."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate_token(self, token_data: dict[str, Any], portfolio_value_usdc: float) -> BreakoutDecision:
        """Evaluate one token against the six-factor entry filter."""

        symbol = str(token_data.get("symbol", "")).upper()
        position_size = portfolio_value_usdc * self.settings.max_position_pct
        if not is_tradable_symbol(symbol):
            return BreakoutDecision(
                should_enter=False,
                symbol=symbol or None,
                position_size_usdc=0.0,
                factor_scores={},
                true_factor_count=0,
                reason="symbol outside tradable target allowlist",
            )

        volume_1h = self._positive_number(token_data.get("volume_1h"))
        rolling_avg = self._positive_number(token_data.get("rolling_24h_hourly_volume_avg"))
        price = self._positive_number(token_data.get("price"))
        high_6h = self._positive_number(token_data.get("high_6h"))
        bnb_trend = self._nonzero_number(token_data.get("bnb_1h_trend_pct"))
        rsi = self._positive_number(token_data.get("rsi"))
        slippage = self._positive_number(token_data.get("estimated_slippage_pct"))
        funding_rate = self._nonzero_number(token_data.get("funding_rate"))
        open_interest_change = self._nonzero_number(token_data.get("open_interest_change_pct"))
        derivatives_available = funding_rate is not None and open_interest_change is not None
        broad_derivatives_risk = (
            derivatives_available
            and (abs(funding_rate) > 0.0015 or open_interest_change < -10.0)
        )

        slippage_under_cap = slippage is not None and slippage < self.settings.max_slippage_pct
        factor_scores = {
            "volume_breakout": (
                volume_1h is not None
                and rolling_avg is not None
                and volume_1h > 2 * rolling_avg
            ),
            "six_hour_high_break": price is not None and high_6h is not None and price > high_6h,
            "regime_not_risk_off": bnb_trend is not None and bnb_trend > -2.0,
            "rsi_in_range": rsi is not None and 55.0 <= rsi <= 75.0,
            "slippage_under_cap": slippage_under_cap,
            "derivatives_risk_clear": derivatives_available and not broad_derivatives_risk,
        }
        true_factor_count = sum(1 for passed in factor_scores.values() if passed)
        should_enter = true_factor_count >= self.settings.min_entry_factors and slippage_under_cap
        if should_enter:
            reason = f"{true_factor_count}/6 factors passed"
        elif not slippage_under_cap:
            reason = "slippage estimate missing, zero, or above cap"
        else:
            reason = f"insufficient signal: {true_factor_count}/6 factors passed"
        return BreakoutDecision(
            should_enter=should_enter,
            symbol=symbol,
            position_size_usdc=position_size if should_enter else 0.0,
            factor_scores=factor_scores,
            true_factor_count=true_factor_count,
            reason=reason,
        )

    def evaluate_universe(
        self,
        market_snapshot: dict[str, dict[str, Any]],
        portfolio_value_usdc: float,
    ) -> BreakoutDecision:
        """Scan target symbols and pick the highest-scoring candidate."""

        best_decision: BreakoutDecision | None = None
        best_volume = -1.0
        for symbol, token_data in market_snapshot.items():
            if not is_tradable_symbol(symbol):
                continue
            enriched_data = {"symbol": symbol.upper(), **token_data}
            decision = self.evaluate_token(enriched_data, portfolio_value_usdc)
            volume = self._positive_number(enriched_data.get("volume_1h")) or 0.0
            if best_decision is None:
                best_decision = decision
                best_volume = volume
                continue
            if decision.true_factor_count > best_decision.true_factor_count:
                best_decision = decision
                best_volume = volume
            elif decision.true_factor_count == best_decision.true_factor_count and volume > best_volume:
                best_decision = decision
                best_volume = volume

        if best_decision is None:
            return BreakoutDecision(
                should_enter=False,
                symbol=None,
                position_size_usdc=0.0,
                factor_scores={},
                true_factor_count=0,
                reason="no target symbols available",
            )
        return best_decision

    @staticmethod
    def _positive_number(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number <= 0:
            return None
        return number

    @staticmethod
    def _nonzero_number(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number == 0:
            return None
        return number
