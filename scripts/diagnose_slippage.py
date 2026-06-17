#!/usr/bin/env python3
"""Diagnose whether slippage is being gathered, and if not, why.

Two independent checks:

1. LOG ANALYSIS (default, runs anywhere, no creds needed):
   Reads the decision log and reports the entry-score distribution, action and
   reason breakdown, and — crucially — for the candidates that cleared the quote
   floor, how many actually received a slippage quote. Slippage is only quoted
   for candidates scoring >= (BREAKOUT_ENTRY_SCORE_MIN - BREAKOUT_QUOTE_SCORE_BUFFER),
   so a blank slippage on a low-scoring candidate is correct, not a bug.

2. LIVE QUOTE PROBE (--live, run on the box with TWAK creds):
   Calls TWAKInterface.estimate_slippage_pct directly on a few liquid tokens to
   prove the quote path works independently of the scoring gate. Quote-only — it
   never swaps or moves funds.

Usage:
    python -m scripts.diagnose_slippage                       # log analysis
    python -m scripts.diagnose_slippage --log logs/decision_live.jsonl
    python -m scripts.diagnose_slippage --live               # + probe TWAK quotes
    python -m scripts.diagnose_slippage --live --amount 20 --tokens ETH,CAKE,BNB
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _num(value: object) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _slippage_field(row: dict) -> float | None:
    # Schema has drifted across runs; accept either name.
    for key in ("slippage_quote", "estimated_slippage_pct"):
        val = _num(row.get(key))
        if val is not None:
            return val
    return None


def _reasons(row: dict) -> list[str]:
    rs = row.get("reasons")
    if isinstance(rs, list):
        return [str(x) for x in rs]
    for key in ("reasons", "reason"):
        if row.get(key):
            return [str(row[key])]
    return []


def analyze_log(log_path: Path, quote_floor: float) -> int:
    if not log_path.exists():
        print(f"[!] log not found: {log_path}")
        return 1
    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not rows:
        print(f"[!] no parseable rows in {log_path}")
        return 1

    print(f"== {log_path} :: {len(rows)} decisions ==\n")

    actions = Counter(r.get("action") for r in rows)
    print("actions:", dict(actions))

    scores = sorted(s for r in rows if (s := _num(r.get("entry_score"))) is not None)
    if scores:
        n = len(scores)
        print(
            f"\nentry_score (n={n}): min={scores[0]:.1f} "
            f"median={scores[n // 2]:.1f} max={scores[-1]:.1f}"
        )
        cleared = [s for s in scores if s >= quote_floor]
        print(f"  cleared quote floor ({quote_floor:.0f}): {len(cleared)}/{n}")
    else:
        print("\nentry_score: not present on these rows")
        cleared = []

    # Health metric: of candidates that cleared the floor, how many got a quote?
    quoted = 0
    cleared_rows = 0
    for r in rows:
        s = _num(r.get("entry_score"))
        if s is None or s < quote_floor:
            continue
        cleared_rows += 1
        if _slippage_field(r) is not None:
            quoted += 1
    print("\nSLIPPAGE GATHERING HEALTH:")
    if cleared_rows == 0:
        print("  No candidate ever cleared the quote floor → slippage path never exercised.")
        print("  This is a SCORING/THRESHOLD/market issue, not a slippage bug.")
    else:
        pct = 100 * quoted / cleared_rows
        print(f"  {quoted}/{cleared_rows} floor-clearing candidates got a slippage quote ({pct:.0f}%).")
        if quoted < cleared_rows:
            print("  [!] Some floor-clearers had NO quote → investigate the TWAK quote path.")
        else:
            print("  [ok] Every qualifying candidate was quoted. Slippage gathering works.")

    all_slip = [v for r in rows if (v := _slippage_field(r)) is not None]
    if all_slip:
        print(f"  observed slippage quotes (sample): {all_slip[:8]}")

    rc: Counter = Counter()
    for r in rows:
        for reason in _reasons(r):
            rc[reason[:60]] += 1
    print("\ntop reasons:")
    for reason, c in rc.most_common(10):
        print(f"  {c:4d}  {reason}")
    return 0


def probe_live(amount: float, tokens: list[str], stable: str) -> int:
    try:
        from src.execution.twak_interface import TWAKInterface
    except Exception as exc:  # pragma: no cover - depends on runtime deps
        print(f"[!] cannot import TWAKInterface ({exc}). Run this on the box with deps installed.")
        return 1

    twak = TWAKInterface(paper_trade=True)
    print(f"\n== LIVE TWAK quote probe (quote-only, no swaps) :: ${amount} {stable}->TOKEN ==")
    failures = 0
    for token in tokens:
        try:
            slip = twak.estimate_slippage_pct(amount, stable, token)
        except Exception as exc:
            print(f"  {token:6s} ERROR: {exc}")
            failures += 1
            continue
        if slip is None:
            print(f"  {token:6s} quote returned None (no usable quote)")
            failures += 1
        else:
            print(f"  {token:6s} slippage = {slip * 100:.3f}%")
    if failures:
        print(f"\n[!] {failures}/{len(tokens)} quotes failed → the TWAK quote path itself is the problem.")
        return 1
    print("\n[ok] TWAK quote path works. Any blank slippage in logs is the scoring gate, not the quote.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--log", default="logs/decision_live.jsonl")
    p.add_argument("--entry-min", type=float, default=45.0, help="BREAKOUT_ENTRY_SCORE_MIN")
    p.add_argument("--buffer", type=float, default=5.0, help="BREAKOUT_QUOTE_SCORE_BUFFER")
    p.add_argument("--live", action="store_true", help="also probe TWAK quotes (needs creds)")
    p.add_argument("--amount", type=float, default=20.0)
    p.add_argument("--tokens", default="ETH,CAKE,BNB")
    p.add_argument("--stable", default="USDC")
    args = p.parse_args()

    quote_floor = max(0.0, args.entry_min - args.buffer)
    rc = analyze_log(Path(args.log), quote_floor)
    if args.live:
        rc = probe_live(args.amount, [t.strip().upper() for t in args.tokens.split(",") if t.strip()], args.stable) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
