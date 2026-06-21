# Fix breakout logging and make RSI band configurable

## Summary

Three small, targeted fixes:

1. **Correct the misleading "no 6h reference" log**
2. **Make the RSI entry band configurable via environment variables**
3. **Ensure BNB is always included as a regime-reference enrichment target**

---

## Fix 1 — Expose `six_reference` through `_BreakoutProfile`

### Problem

The decision log showed every candidate returning:

```json
{ "six_hour_high_break": "price X · no 6h reference" }
```

even when the price cache contained 24h+ of history and a valid 6h high existed.

The root cause was that the candidate's `last_reference_high` field was set from `breakout_profile.broken_reference_high`, which is only non-None when price actually clears the reference. When price was below the reference, `last_reference_high` became `None` and the logging code always fell through to the "no 6h reference" branch, hiding the real 6h high from operators.

### Change

- Added `six_reference: float | None = None` to `_BreakoutProfile`.
- `_breakout_profile()` now returns the computed 6h reference (`references.get(6)`) in that field.
- `_cheap_candidate()` now sets `last_reference_high=breakout_profile.six_reference` instead of `broken_reference_high`.

This makes the "price X · 6h high Y" log branch reachable and accurate when price is below the 6h reference.

---

## Fix 2 — Configurable RSI band

### Problem

The RSI in-range check was hardcoded to `55.0 <= rsi <= 75.0`, and the factor metric log repeated the same fixed band. Live symbols were printing RSIs in the 41–53 range, so the gate permanently blocked entries even with `entries_allowed: true`. Tuning the band required a code change.

### Change

- Added two new settings in `src/config/settings.py`:
  - `breakout_rsi_lower: float = 55.0`
  - `breakout_rsi_upper: float = 75.0`
- Wired them to environment variables in `load_settings()`:
  - `BREAKOUT_RSI_LOWER`
  - `BREAKOUT_RSI_UPPER`
- Replaced the hardcoded check in `breakout_engine.py` with the configured bounds.
- Updated the RSI metric log strings to display the configured band.

### Backward compatibility

Default values are unchanged (`55–75`), so existing behaviour is preserved unless the environment variables are explicitly overridden.

---

## Fix 3 — Always include BNB as regime-reference enrichment target

### Problem

A recent change filtered stablecoins and momentum-excluded symbols from enrichment ranking before applying the `must_have` set. BNB is not present in the eligible target allowlist, so it was dropped from `targets` and the guard `symbol not in targets` prevented `must_have` from re-adding it. The test `test_select_enrichment_symbols_caps_to_top_n_with_positions` failed with:

```
AssertionError: assert 'BNB' in ['CAKE', 'UNI', 'AAVE']
```

### Change

- In `src/data/enrichment_planner.py`, removed the `symbol not in targets` guard for `must_have` symbols so BNB and open positions are always enriched regardless of allowlist membership.

---

## Files changed

- `src/config/settings.py`
- `src/strategy/6falgorithm/breakout_engine.py`
- `src/data/enrichment_planner.py`

## Testing

Ran `pytest tests/`:

- `tests/test_breakout_engine.py` — 57 passed, 2 skipped.
- `tests/test_snapshot_persistence_and_dust.py` — 12 passed.
- Full suite — **443 passed, 5 skipped**.
