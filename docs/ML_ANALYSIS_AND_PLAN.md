# Cascade-AI ML Layer: State Analysis, Competitive Benchmark & Action Plan

**Date:** 2026-06-18 (UTC)  
**Hackathon:** BNB Hack — AI Trading Agent Edition (Track 1: Autonomous Trading Agents)  
**Build Window:** Ends June 21, 2026 (3 days remaining)  
**Live Trading Window:** June 22–28, 2026 (7 days)  
**Prize Pool:** $24,000 (Track 1) + $6,000 in special prizes

---

## 1. Executive Summary: The Timeline Reality

**The critical constraint is time.** There are 3 days left in the build window and the live trading competition starts in 4 days. This is not enough time to train, validate, and deploy a production ML model that can safely override a rule-based engine with real money at stake.

**The correct strategy for this hackathon is:**
1. **Keep the deterministic rule-based engine as the sole live decision-maker** during the competition week.
2. **Use the ML layer as a shadow/advisory system** to score entries and accumulate data.
3. **Fix data plumbing** so every trade outcome is captured with proper `trade_id` pairing.
4. **Deploy a lightweight, pre-trained regime model** for position-sizing modulation (not entry gating).
5. **Focus hackathon scoring on the non-ML criteria**: TWAK integration depth, x402 usage, autonomous execution, and real PnL from the solid rule-based system.

The ML infrastructure is actually **well-architected** (shadow-first, fail-closed, feature parity tests, no train/serve skew). The problem is that it has not been trained because the data pipeline has leaks, and even when fixed, 3 days of trading cannot produce enough labels for a reliable model.

---

## 2. Current State Analysis

### 2.1 Architecture Overview

The project has **two parallel ML stacks** — this is a maintenance liability and a source of confusion:

| Stack | Location | Purpose | Status | Artifacts |
|-------|----------|---------|--------|-----------|
| **Legacy Regime Pipeline** | `src/ml/` | Market regime classification (momentum vs. chop) | Trained, but weak | `regime_lgb_v2.pkl` (AUC 0.58) |
| **Entry-Quality Shadow Pipeline** | `src/research/` | Predict whether a specific entry candidate will be profitable | Not trained | No artifact yet |

#### Legacy Regime Pipeline (`src/ml/`)
- **Feature pipeline:** 41 features combining OHLCV (ret_1, ret_4, RSI, ATR, EMA spreads), CMC snapshots, cross-token features, and strategy features.
- **Model:** LightGBM classifier.
- **Performance:** Mean AUC 0.58, worst fold 0.52, std 0.046. This is **barely above random** (0.50).
- **Usage:** Loaded by `RegimePredictor`, but `ml_enabled` is `False` in settings. It does not influence live trades.
- **Problem:** Trained on historical OHLCV data (likely synthetic or limited), but the model has no predictive edge. It should not be trusted for live capital decisions.

#### Entry-Quality Shadow Pipeline (`src/research/`)
- **Design:** Excellent. Shadow-first, fail-closed, zero capital risk.
- **Feature contract:** `entry_feature_vector()` is the single source of truth. Used by both training and live shadow. No train/serve skew.
- **Training script:** `src/research/train.py` — walk-forward TimeSeriesSplit, LogReg + LightGBM, PnL-vs-rule gate.
- **Shadow serving:** `src/strategy/model_predictor.py` + `src/research/shadow_decisions.py`.
- **Status:** `enable_model_shadow = False`. No artifact exists because `trade_outcomes.jsonl` has **zero properly paired entry/exit trades**.

### 2.2 Data Situation (Critical)

**Trade outcomes log:** `logs/trade_outcomes.jsonl`
- **22 entry events**, **19 exit events**.
- **0 paired by `trade_id`**. Every entry has a `trade_id`, but **no exit event has a `trade_id`**. The `trade_id` field is `null` on all exits.
- The `_join_by_trade_id` function therefore returns an empty DataFrame, and the dataset falls back to `_join_by_symbol_time` (first-exit-after-entry heuristic). This is fragile and can match the wrong exit to an entry.
- **Bottom line:** the label-generation pipeline is broken. Even if we had 1,000 trades, the current code would fail to pair most of them.

**Historical OHLCV data:** `data/historical/`
- `binance/` directory with 15m candle data.
- `feature_matrix.parquet` exists (1.9MB, built June 17).
- This is used by the **legacy regime model**, not the entry-quality model.

**CMC quote database:** `data/cmc_premium.db` (20KB SQLite)
- Written by `scripts/cmc_feature_collector.py` every 30 minutes.
- Intentionally excluded from the entry-quality model because the live snapshot cannot reproduce the collector schema 1:1. This is a correct design choice to avoid train/serve skew.

### 2.3 Model Artifacts

| Artifact | Path | Size | Trained | AUC |
|----------|------|------|---------|-----|
| `regime_lgbm_v1.pkl` | `models/` | 2.7MB | Unknown | ~0.58 |
| `regime_lgb_v2.pkl` | `models/` | 2.7MB | June 17 | 0.58 |
| `entry_quality_v1.pkl` | `models/` | — | — | — |

### 2.4 Shadow Infrastructure

The shadow logger (`shadow_decisions.py`) writes two variants per cycle:
1. `jump_inspired` — BNB regime proxy (momentum_10, sortino proxies). Currently logging to `decision_shadow.jsonl` (144 rows).
2. `trained_model` — entry-quality model on the live candidate. **Never logs** because `enable_model_shadow = False` and no artifact exists.

---

## 3. Comparison with Successful Open-Source ML Trading Repositories

### 3.1 Repositories Analyzed

| Repository | Stars | Language | ML Approach | Key Strength |
|------------|-------|----------|-------------|--------------|
| **Freqtrade** | ~50K | Python | Strategy hyperopt + ML | Extensive backtesting, hyperopt, risk management, large community |
| **Qlib (Microsoft)** | ~34K | Python | Supervised + RL + market dynamics | Full research→production pipeline, Alpha-driven features, walk-forward CV |
| **TradingAgents** | ~25K | Python | Multi-Agent LLM framework | LLM-based reasoning, multi-agent consensus, interpretable decisions |
| **FinRL** | ~13K | Python | Deep RL | DRL environments for portfolio allocation, extensive benchmarks |
| **Abu Quant** | ~15K | Python | ML + grid search | Chinese market focus, rich metrics, cross-validation |
| **Polymarket Copy-Trading Bot** | ~391 | Python | Rule-based + risk filters | Position tracking, stop-loss, position sizing |
| **Cross-Market State Fusion** | ~326 | Python | RL | Binance Futures data fusion, state-space modeling |

### 3.2 What Successful Projects Do That This Project Does Not (Yet)

#### A. Data Volume & Quality
- **Successful projects:** Start with **months to years** of OHLCV data, on-chain data, sentiment, and derivatives. Qlib provides pre-built datasets. Freqtrade users backtest on 10,000+ candles before going live.
- **This project:** 22 entries / 19 exits, and the pairing is broken. The rule engine has been running but its outcomes are not being captured correctly.

#### B. Feature Engineering Depth
- **Successful projects:** Qlib computes 100+ alpha factors (price-volume, momentum, mean-reversion, volatility). Freqtrade supports custom feature pipelines with `ta-lib` + `ta` + `pandas-ta`.
- **This project:** The legacy regime pipeline has 41 features (good start). The entry-quality pipeline uses only ~10 features (`factor_*`, `entry_score`, `regime`, `bnb_pct`) — this is intentionally minimal to avoid train/serve skew, but it is too minimal to capture market nuances.

#### C. Validation & Backtesting
- **Successful projects:** Freqtrade has `backtesting`, `edge`, and `hyperopt` commands. Qlib uses **purged cross-validation** and **nested walk-forward** to prevent leakage. FinRL has dedicated train/validation/test environments.
- **This project:** The entry-quality pipeline uses `TimeSeriesSplit` (correct), but with only 22 trades, 3 folds are meaningless. The PnL-vs-rule gate is a good idea but cannot trigger with no data.

#### D. Model Diversity
- **Successful projects:** Ensemble methods (Random Forest + Gradient Boosting + Neural Net). Qlib supports LightGBM, XGBoost, CatBoost, and PyTorch models. Freqtrade supports `Catboost`, `XGBoost`, `LightGBM`, and neural networks via `freqtrade-ml`.
- **This project:** Only LogReg + LightGBM tried. Only LightGBM trained for regime. No ensemble, no hyperparameter search, no model stacking.

#### E. Risk Integration
- **Successful projects:** Risk is built into the **strategy layer** (stop-loss, trailing stop, max drawdown, position sizing). ML is used for **alpha generation** or **regime detection**, but risk rules are hardcoded and never overridden by a model.
- **This project:** Risk is actually **better** than most open-source projects here. The guardrails (drawdown soft stop 10%, kill switch 18%, daily loss cap, max slippage, position size caps) are robust. The ML is correctly isolated as advisory only. This is a strength, not a weakness.

#### F. Deployment & Monitoring
- **Successful projects:** Docker containers, CI/CD, health checks, dashboard. Freqtrade has a built-in web UI.
- **This project:** Has health server, systemd services, Telegram alerts, log rotation, and a Next.js dashboard. This is competitive.

### 3.3 What This Project Does Better Than Most

1. **Fail-closed ML design:** The model can only disable itself or advise; it can never open a trade. Most open-source bots give ML direct control.
2. **Train/serve parity:** `feature_contract.py` is a dependency-free, single-source-of-truth module. This is a production-grade pattern rarely seen in open-source trading bots.
3. **x402 micropayment integration:** Paying per-request for CMC data via on-chain payments is unique and directly addresses the hackathon's "Best Use of x402" special prize.
4. **TWAK integration:** Self-custody signing via Trust Wallet Agent Kit is native, not bolted-on.
5. **Shadow-first ML:** Logging hypothetical model decisions without trading capital is a best practice from institutional quant firms, not typical in OSS.

---

## 4. Gap Analysis: Where Are We vs. Where We Need to Be?

| Dimension | Current State | Hackathon Requirement | Gap Severity |
|-----------|---------------|----------------------|--------------|
| **ML Model Trained** | Regime model (weak AUC); Entry model untrained | Not required for Track 1 (PnL wins) | Medium |
| **Data Quality** | 22 entries, 0 paired by trade_id | Need clean outcomes for post-hackathon ML | **Critical** |
| **Feature Depth** | 10 entry features, 41 regime features | More features = better edge if data exists | Medium |
| **Risk Management** | Excellent (drawdown, kill switch, slippage) | Must survive 30% max drawdown | **Strength** |
| **TWAK Depth** | Signing works, but single-surface | Needs multi-surface (signing, autonomous, x402) for special prize | Medium |
| **Live Trading** | Paper trade mode on | Must trade live June 22–28 | **Critical** |
| **Registration** | `compete_registered.json` exists | Must register on-chain before June 22 | Need to verify |
| **Min Trade Count** | 3/day max | 1/day minimum (7 total) | Manageable |
| **Dashboard / Demo** | Next.js dashboard exists | Needs demo video for judging | Medium |

---

## 5. Strategic Recommendations

Given 3 days until the build window closes and 4 days until live trading, the strategy must be **ruthlessly pragmatic**.

### 5.1 Do NOT Do These Things (Time Wasters)

1. **Do not attempt to train a live entry-quality model and put it in charge.** 22 trades with broken pairing is not enough data. A model trained now would be noise and could cause disqualification via bad trades or drawdown.
2. **Do not rewrite the feature pipeline.** The current `feature_contract.py` is correct. Expanding it now risks introducing train/serve skew before the competition.
3. **Do not add deep learning or RL.** Not enough data, not enough time, and the infrastructure is not ready for RL environments.
4. **Do not switch to a new modeling framework.** Stick to scikit-learn + LightGBM.

### 5.2 DO These Things (High Impact, Low Risk)

#### Immediate (Today, June 18)

1. **Fix the `trade_id` pairing in exits.**
   - The exit logging path must capture the `trade_id` from the matching entry.
   - Without this, the ML dataset builder will always fall back to symbol/time heuristics, which is wrong.
   - **File to fix:** `src/execution/execution_log.py` or `src/research/trade_outcome_log.py` — ensure `trade_id` is threaded through the position lifecycle.

2. **Verify on-chain registration.**
   - Check `compete_registered.json` and confirm the agent wallet is registered on the competition contract (`0x212c61b9b72c95d95bf29cf032f5e5635629aed5`).
   - If not registered, run `twak compete register` or the MCP `competition_register` action immediately.

3. **Confirm live trading readiness.**
   - `paper_trade = False` must be set in `.env` for the competition.
   - Ensure the wallet has BNB for gas and USDC for trading.
   - Ensure the wallet holds non-zero balances of at least one in-scope asset before June 22.

4. **Enable the legacy regime model for advisory sizing only.**
   - The `regime_lgb_v2` model has AUC 0.58 — not enough for entry decisions, but enough to **modulate position size**.
   - Example: if regime = "momentum", use 1.0x position size. If "chop", use 0.5x. If "risk_off", use 0.1x (already hardcoded).
   - This is **low risk** because the rule engine still controls entry/exit, and the size multiplier already exists in `RegimeResult`.
   - **Do not** enable `ml_enabled` for entry gating. Only use the existing `regime_detector.py` sizing logic.

#### Day 2 (June 19)

5. **Run a 24-hour paper-trade stress test.**
   - Let the bot run for a full day with `paper_trade=True`.
   - Verify that exits now carry the correct `trade_id`.
   - Check `logs/trade_outcomes.jsonl` for paired entries.
   - Run `scripts/diagnose_trades.py` to confirm the count.

6. **Train the entry-quality model on the newly fixed data (even if small).**
   - After 24 hours of paper trading, you may have 5–10 new closed trades.
   - Combined with historical data, you might reach ~30 rows (the `min_training_rows` threshold).
   - Run `python -m src.research.train` and inspect the `model_card.json`.
   - **If the promotion gate fails** (which is likely), do not deploy. Just keep the artifact for analysis.
   - **If the gate passes** (unlikely with <50 trades), copy the artifact to the trading box and enable `ENABLE_MODEL_SHADOW=true`.
   - The shadow will start logging `trained_model` variants to `decision_shadow.jsonl` without touching trades.

7. **Enable `factor_matrix_log_enabled` for one day.**
   - This writes one row per symbol per cycle with all factor booleans and raw scores.
   - It is heavy but invaluable for post-hackathon analysis. Run it for 24 hours, then disable it before the competition to save disk and I/O.

#### Day 3 (June 20)

8. **Switch to `paper_trade=False` and do final preflight.**
   - Run `python -m src.main preflight`.
   - Verify TWAK wallet unlock, BSC balances, CMC snapshot, and quote-only TWAK swap.
   - Ensure `COMPETITION_END_UTC` is set (e.g., `2026-06-28T23:59:59+00:00`) so the bot auto-liquidates before the deadline.

9. **Record the demo video.**
   - The hackathon judges score "Demo and presentation" (5–10% of special prizes).
   - Show: preflight checks, live trading loop, on-chain tx hashes, dashboard, and the x402 payment flow.
   - Keep it under 3 minutes.

### 5.3 During Live Trading (June 22–28)

10. **Monitor but do not intervene.**
    - The rule engine is designed to run hands-off.
    - Daily checks: verify at least 1 trade executed (compliance minimum).
    - If the kill switch triggers (18% drawdown), the bot will liquidate and enter capital-preservation mode. It will still attempt the daily compliance trade.

11. **Collect shadow data.**
    - If shadow mode is enabled, every cycle will log both the rule engine decision and the model's hypothetical decision.
    - After the competition, this data becomes the training set for a real model.

12. **Avoid the drawdown disqualification.**
    - The competition disqualifies at 30% drawdown. Your kill switch is at 18%, giving a 12% buffer.
    - Do not override the kill switch. Do not increase position sizes mid-competition.

---

## 6. Post-Hackathon ML Roadmap (June 29+)

After the competition, you will have 7 days of live trading data (hopefully 20+ closed trades). This is when the ML layer should be built out properly.

### Phase 1: Data Consolidation (Week 1)
- Fix the `trade_id` propagation once and for all (entry → position manager → exit).
- Set up S3 + DuckDB sync for logs (as recommended in `ML_STATE_AND_NEXT_STEPS.md`).
- Merge the two ML stacks into a single `src/ml/` directory with clear submodules:
  - `src/ml/regime/` — market regime detection (keep the existing model, retrain with more data).
  - `src/ml/entry_quality/` — the current `src/research/` pipeline.
  - `src/ml/features/` — unified feature contract.

### Phase 2: Feature Expansion (Week 2)
- Re-add CMC features to the entry-quality model via a shared snapshot→feature builder (the current blocker).
- Add on-chain features: wallet flow, DEX volume, gas price trend.
- Add sentiment features: Fear & Greed, funding rates, social volume (CMC Agent Hub data).

### Phase 3: Model Improvement (Week 3–4)
- Hyperparameter tuning with Optuna (already installed via `scripts/optimize_params.py`).
- Ensemble: LightGBM + XGBoost + CatBoost + LogReg meta-learner.
- Purged cross-validation (already partially implemented in `src/ml/cv.py`).
- Retrain the regime model with the expanded feature set; target AUC > 0.65 before any live influence.

### Phase 4: Advisory → Influence (Week 5+)
- Only when the entry-quality model consistently beats the rule engine on shadow PnL:
  - Wire it as a **confidence multiplier** on the breakout score.
  - Or as a **veto** on candidates below 0.55 probability.
  - Never as the sole entry trigger.
- A/B test: 50% of candidates use the model multiplier, 50% use pure rule. Compare realized PnL.

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Trade IDs not fixed in time | Medium | High | Fallback `_join_by_symbol_time` works for single-position symbols; test immediately |
| Regime model AUC stays <0.60 | High | Low | Do not use it for live entry gating; only for sizing |
| Drawdown hits 30% during comp | Low | Critical | Kill switch at 18%, position cap 5%, max 3 trades/day |
| Bot fails to make 7 trades | Low | Disqualification | Compliance trade logic exists; monitor daily |
| x402 budget runs out | Medium | Medium | $15 total budget, ~$0.01/call = 1,500 calls; more than enough |
| TWAK signing fails | Low | Critical | Preflight checks every startup; systemd auto-restart |

---

## 8. Checklist: Next 72 Hours

### June 18 (Today)
- [ ] Fix `trade_id` propagation from entry to exit in `trade_outcome_log.py` or `execution_log.py`.
- [ ] Verify `compete_registered.json` and on-chain registration.
- [ ] Ensure wallet has BNB + USDC + at least one in-scope token (e.g., CAKE, TWT).
- [ ] Confirm `paper_trade=False` is ready to flip.
- [ ] Review `COMPETITION_END_UTC` and `flatten_before_end_minutes` settings.

### June 19
- [ ] Run 24-hour paper trade with `factor_matrix_log_enabled=true`.
- [ ] Verify paired trades in `trade_outcomes.jsonl`.
- [ ] Train entry-quality model on accumulated data (expect gate to fail — this is fine).
- [ ] If artifact exists, enable `ENABLE_MODEL_SHADOW=true` for data collection.

### June 20
- [ ] Disable `factor_matrix_log_enabled` to save I/O.
- [ ] Switch to `paper_trade=False`.
- [ ] Run full preflight: `python -m src.main preflight`.
- [ ] Record 3-minute demo video.
- [ ] Submit project on DoraHacks with repo link and demo.

### June 21 (Build Window Ends)
- [ ] Final code freeze. No more changes.
- [ ] Monitor bot for 12 hours in live mode to confirm stability.
- [ ] Ensure systemd services are running: `cascade-ai.service`, `cascade-ai-collector.timer`.

### June 22 (Live Trading Starts)
- [ ] Confirm at least 1 trade executes today.
- [ ] Check dashboard for portfolio value and drawdown.
- [ ] Do not touch the bot unless the kill switch fires.

---

## 9. Conclusion

The Cascade-AI project has a **solid rule-based trading engine** and a **well-architected ML shadow layer**. The mistake would be trying to rush the ML model into live decisions before it has data and validation. The winning strategy for this hackathon is:

1. **Ship what works** — the rule engine, TWAK integration, x402 payments, and autonomous execution.
2. **Collect data silently** — fix trade IDs, enable shadow logging, and let the ML infrastructure prove itself offline.
3. **Win on PnL and integration depth** — not on ML sophistication. The judges care about real returns and technical execution.
4. **Build the ML model after the competition** — when you have 30+ clean labeled trades and the time to iterate properly.

The infrastructure is there. The discipline to keep ML in shadow until it earns its place is what separates a robust trading system from a gambling bot.
