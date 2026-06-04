"""Tests for the breakout engine."""

from __future__ import annotations

from src.config.settings import Settings
from src.config.tokens import ELIGIBLE_149_SYMBOLS
from src.strategy.breakout_engine import BreakoutEngine


def _token(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "symbol": "CAKE",
        "price": 10.5,
        "volume_1h": 2100.0,
        "rolling_24h_hourly_volume_avg": 1000.0,
        "high_6h": 10.0,
        "bnb_1h_trend_pct": -3.0,
        "rsi": 62.0,
        "estimated_slippage_pct": 0.005,
        "funding_rate": 0.002,
        "open_interest_change_pct": -1.0,
    }
    data.update(overrides)
    return data


def test_four_of_six_true_enters() -> None:
    engine = BreakoutEngine(Settings())
    decision = engine.evaluate_token(_token(), 10000.0)
    assert decision.should_enter is True
    assert decision.true_factor_count == 4
    assert decision.position_size_usdc == 500.0


def test_stablecoin_targets_are_not_directional_entries() -> None:
    engine = BreakoutEngine(Settings())

    decision = engine.evaluate_token(_token(symbol="USDC", bnb_1h_trend_pct=0.1, funding_rate=0.0), 10000.0)

    assert decision.should_enter is False
    assert decision.reason == "symbol outside tradable target allowlist"


def test_high_rsi_weakens_score() -> None:
    engine = BreakoutEngine(Settings())
    normal = engine.evaluate_token(_token(), 10000.0)
    hot = engine.evaluate_token(_token(rsi=81.0), 10000.0)
    assert hot.factor_scores["rsi_in_range"] is False
    assert hot.true_factor_count == normal.true_factor_count - 1


def test_universe_chooses_highest_scoring_target_token() -> None:
    engine = BreakoutEngine(Settings())
    snapshot = {
        "NOTREAL": _token(symbol="NOTREAL", volume_1h=999999.0),
        "CAKE": _token(volume_1h=3000.0, estimated_slippage_pct=0.02),
        "LINK": _token(symbol="LINK", volume_1h=2200.0, bnb_1h_trend_pct=0.1, funding_rate=0.0),
    }
    decision = engine.evaluate_universe(snapshot, 10000.0)
    assert decision.symbol == "LINK"
    assert decision.should_enter is True


def test_missing_or_zero_data_fails_closed() -> None:
    engine = BreakoutEngine(Settings())
    decision = engine.evaluate_token(
        _token(
            rsi=None,
            estimated_slippage_pct=0.0,
            funding_rate=0.0,
            open_interest_change_pct=0.0,
            volume_1h=None,
            bnb_1h_trend_pct=0.0,
        ),
        10000.0,
    )

    assert decision.factor_scores["volume_breakout"] is False
    assert decision.factor_scores["regime_not_risk_off"] is False
    assert decision.factor_scores["rsi_in_range"] is False
    assert decision.factor_scores["slippage_under_cap"] is False
    assert decision.factor_scores["derivatives_risk_clear"] is False
    assert decision.should_enter is False


def test_missing_slippage_blocks_entry_even_when_other_factors_pass() -> None:
    engine = BreakoutEngine(Settings())
    decision = engine.evaluate_token(
        _token(
            bnb_1h_trend_pct=0.1,
            estimated_slippage_pct=None,
            funding_rate=0.0001,
            open_interest_change_pct=1.0,
        ),
        10000.0,
    )

    assert decision.true_factor_count == 5
    assert decision.factor_scores["slippage_under_cap"] is False
    assert decision.should_enter is False
    assert decision.reason == "slippage estimate missing, zero, or above cap"


def test_eligible_rules_list_contains_149_entries() -> None:
    assert len(ELIGIBLE_149_SYMBOLS) == 149
