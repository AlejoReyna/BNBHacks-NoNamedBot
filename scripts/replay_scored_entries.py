#!/usr/bin/env python3
"""Replay decision logs to calibrate the scored breakout threshold.

The June 12 dashboard export contains one logged/telemetry candidate per cycle,
not the full raw market snapshot. When historical rows lack ``entry_score`` the
replay uses the frozen boolean factors as the evidence base and simulates
position exclusion by counting each symbol once after its first entry.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from src.config.tokens import is_momentum_candidate_symbol, is_tradable_symbol
except Exception:  # pragma: no cover - script can still replay exported logs outside the repo.
    is_momentum_candidate_symbol = None
    is_tradable_symbol = None


DEFAULT_WEIGHTS = {
    "breakout": 35.0,
    "volume": 25.0,
    "momentum": 15.0,
    "rsi": 10.0,
    "derivatives": 10.0,
    "macro": 5.0,
}


def load_decisions(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("{") or text.startswith("["):
        payload = json.loads(text)
        if isinstance(payload, dict):
            items = payload.get("items", [])
        else:
            items = payload
        return [item for item in items if isinstance(item, dict)]
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
    return rows


def score_from_row(row: dict[str, Any], weights: dict[str, float]) -> float:
    logged_score = row.get("entry_score")
    if logged_score is not None:
        try:
            return float(logged_score)
        except (TypeError, ValueError):
            pass
    factors = row.get("factor_scores") or {}
    if not isinstance(factors, dict):
        factors = {}
    score = 0.0
    score += weights["breakout"] if factors.get("six_hour_high_break") else 0.0
    score += weights["volume"] if factors.get("volume_breakout") else 0.0
    score += weights["rsi"] if factors.get("rsi_in_range") else 0.0
    score += weights["derivatives"] if factors.get("derivatives_risk_clear") else 0.0
    return score


def replay_entries(
    rows: list[dict[str, Any]],
    *,
    threshold: float,
    weights: dict[str, float],
    max_slippage_pct: float,
    assume_unquoted_slippage_ok: bool,
    respect_allowlist: bool,
) -> list[dict[str, Any]]:
    entered_symbols: set[str] = set()
    entries: list[dict[str, Any]] = []
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        if not symbol or symbol in entered_symbols:
            continue
        if respect_allowlist and is_tradable_symbol is not None and is_momentum_candidate_symbol is not None:
            if not is_tradable_symbol(symbol) or not is_momentum_candidate_symbol(symbol):
                continue
        score = score_from_row(row, weights)
        if score < threshold:
            continue
        slippage = row.get("estimated_slippage_pct")
        if slippage is None:
            if not assume_unquoted_slippage_ok:
                continue
        else:
            try:
                if float(slippage) < 0 or float(slippage) >= max_slippage_pct:
                    continue
            except (TypeError, ValueError):
                continue
        entered_symbols.add(symbol)
        entries.append(
            {
                "timestamp": row.get("timestamp"),
                "symbol": symbol,
                "score": score,
                "slippage": slippage,
            }
        )
    return entries


def load_price_cache_summary(path: Path | None) -> str:
    if path is None or not path.exists():
        return "price_cache_symbols=0"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return "price_cache_symbols=0"
    point_count = 0
    for points in payload.values():
        if isinstance(points, list):
            point_count += len(points)
    return f"price_cache_symbols={len(payload)} price_cache_points={point_count}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--price-cache", type=Path)
    parser.add_argument("--target-min", type=int, default=3)
    parser.add_argument("--target-max", type=int, default=6)
    parser.add_argument("--max-slippage-pct", type=float, default=0.01)
    parser.add_argument(
        "--require-logged-slippage",
        action="store_true",
        help="Count only rows with a logged slippage quote under the cap.",
    )
    parser.add_argument(
        "--ignore-allowlist",
        action="store_true",
        help="Replay every logged symbol, including telemetry-only rows.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_decisions(args.decisions)
    weights = dict(DEFAULT_WEIGHTS)
    assume_unquoted_slippage_ok = not args.require_logged_slippage
    respect_allowlist = not args.ignore_allowlist
    candidates: list[tuple[int, list[dict[str, Any]]]] = []
    for threshold in range(0, 101):
        entries = replay_entries(
            rows,
            threshold=float(threshold),
            weights=weights,
            max_slippage_pct=args.max_slippage_pct,
            assume_unquoted_slippage_ok=assume_unquoted_slippage_ok,
            respect_allowlist=respect_allowlist,
        )
        if args.target_min <= len(entries) <= args.target_max:
            candidates.append((threshold, entries))

    print(f"rows={len(rows)} {load_price_cache_summary(args.price_cache)}")
    print(f"weights={json.dumps(weights, sort_keys=True)}")
    print(f"assume_unquoted_slippage_ok={assume_unquoted_slippage_ok}")
    print(f"respect_allowlist={respect_allowlist}")
    if not candidates:
        print("no threshold produced the requested entry count")
        return 1
    threshold, entries = candidates[-1]
    print(f"recommended_threshold={threshold} entries={len(entries)} target={args.target_min}-{args.target_max}")
    for entry in entries:
        print(
            f"{entry.get('timestamp')} {entry['symbol']} "
            f"score={entry['score']:.1f} slippage={entry.get('slippage')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
