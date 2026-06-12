"""Tests for offline replay and A/B scripts."""

from __future__ import annotations

import json

from scripts.ab_test_runner import run_ab_test
from scripts.replay_scored_entries import DEFAULT_WEIGHTS, load_decisions, replay_entries
from scripts.replay_shadow import replay_decisions


def test_replay_decisions_writes_report(tmp_path: object) -> None:
    live = tmp_path / "live.jsonl"  # type: ignore[operator]
    shadow = tmp_path / "shadow.jsonl"  # type: ignore[operator]
    output = tmp_path / "report.json"  # type: ignore[operator]
    live.write_text(json.dumps({"cycle_id": 1, "action": "ENTER"}) + "\n", encoding="utf-8")
    shadow.write_text(json.dumps({"cycle_id": 1, "hypothetical_action": "WAIT"}) + "\n", encoding="utf-8")
    report = replay_decisions(str(live), str(shadow), output_path=str(output))
    assert report["matched_cycles"] == 1
    assert json.loads(output.read_text(encoding="utf-8"))["cycles_live"] == 1


def test_replay_decisions_handles_missing_logs_edge(tmp_path: object) -> None:
    output = tmp_path / "report.json"  # type: ignore[operator]
    report = replay_decisions(str(tmp_path / "missing-live.jsonl"), str(tmp_path / "missing-shadow.jsonl"), output_path=str(output))  # type: ignore[operator]
    assert report["cycles_live"] == 0


def test_run_ab_test_returns_variant_metrics(tmp_path: object) -> None:
    baseline = tmp_path / "baseline.jsonl"  # type: ignore[operator]
    variant = tmp_path / "variant.jsonl"  # type: ignore[operator]
    baseline.write_text(json.dumps({"action": "ENTER", "estimated_slippage_pct": 0.001}) + "\n", encoding="utf-8")
    variant.write_text(json.dumps({"hypothetical_action": "ENTER", "slippage_quote": 0.002}) + "\n", encoding="utf-8")
    report = run_ab_test(str(baseline), [str(variant)])
    assert report["baseline"]["trades_per_day"] == 1.0
    assert str(variant) in report["variants"]


def test_run_ab_test_handles_empty_files_edge(tmp_path: object) -> None:
    report = run_ab_test(str(tmp_path / "missing.jsonl"), [])
    assert report["baseline"]["avg_slippage"] == 0.0


def test_scored_replay_respects_allowlist_and_unique_symbols(tmp_path: object) -> None:
    decisions = tmp_path / "decisions.json"  # type: ignore[operator]
    decisions.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "timestamp": "2026-06-12T07:17:56+00:00",
                        "symbol": "AAVE",
                        "estimated_slippage_pct": 0.0,
                        "factor_scores": {
                            "volume_breakout": True,
                            "six_hour_high_break": True,
                            "rsi_in_range": True,
                            "derivatives_risk_clear": True,
                        },
                    },
                    {
                        "timestamp": "2026-06-12T09:04:34+00:00",
                        "symbol": "XAUT",
                        "estimated_slippage_pct": None,
                        "factor_scores": {
                            "volume_breakout": True,
                            "six_hour_high_break": False,
                            "rsi_in_range": True,
                            "derivatives_risk_clear": True,
                        },
                    },
                    {
                        "timestamp": "2026-06-12T13:42:37+00:00",
                        "symbol": "BILL",
                        "estimated_slippage_pct": None,
                        "factor_scores": {
                            "volume_breakout": True,
                            "six_hour_high_break": False,
                            "rsi_in_range": True,
                            "derivatives_risk_clear": True,
                        },
                    },
                    {
                        "timestamp": "2026-06-12T13:47:37+00:00",
                        "symbol": "BILL",
                        "estimated_slippage_pct": None,
                        "factor_scores": {
                            "volume_breakout": True,
                            "six_hour_high_break": False,
                            "rsi_in_range": True,
                            "derivatives_risk_clear": True,
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    rows = load_decisions(decisions)
    entries = replay_entries(
        rows,
        threshold=45.0,
        weights=dict(DEFAULT_WEIGHTS),
        max_slippage_pct=0.01,
        assume_unquoted_slippage_ok=True,
        respect_allowlist=True,
    )

    assert [entry["symbol"] for entry in entries] == ["AAVE", "BILL"]
