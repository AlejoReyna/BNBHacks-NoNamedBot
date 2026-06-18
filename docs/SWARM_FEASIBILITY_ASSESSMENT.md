# ML Layer — Swarm Execution Assessment

## Context

The user is asking if an **agent swarm** approach (multiple specialized sub-agents working in parallel) can be used to complete the ML layer before the BNB Hackathon competition window opens (June 22). The `ML_SWARM_PROMPT.md` already defines a 4-agent split with 5 tasks.

**Key discovery:** The ML bundle is ALREADY wired into `main.py`. The `MLFeatureCache` already has column migrations for the new CMC fields. The `record_cmc_metrics()` method already writes all 9 fields. This means **Tasks 2 and 3 are partially done** — the swarm would be finishing work, not starting from scratch.

---

## Verdict: YES, the swarm can work — but only with strict phase-gates

The agent swarm is actually the **best execution strategy** for the remaining 3 days. Here's why:

### 1. The Infrastructure Is Already Built

The previous session wired the ML bundle into the live path. What the swarm needs to do is **fill the data pipeline and train the model**, not rewrite the architecture:

| Component | Status | What Swarm Needs to Do |
|-----------|--------|------------------------|
| MLBundle wired in `main.py` | ✅ Done | Nothing |
| `MLFeatureCache` schema migration | ✅ Done | Verify fear_greed_delta works |
| `record_cmc_metrics()` 9-field write | ✅ Done | Verify CMC client passes fear_greed |
| `RegimePredictor` + `CandidateRanker` | ✅ Done | Nothing |
| `shadow_audit_fields()` logging | ✅ Done | Nothing |
| Dashboard `.passthrough()` ingestion | ✅ Done | Add typed schema (Task 5) |
| Historical data (149 tokens × 6mo) | ❌ Missing | **Task 3 — data fetch** |
| Trained model with AUC ≥ 0.65 | ❌ Missing | **Task 4 — train after data** |
| Fear/greed in CMC snapshot | ❌ Missing | **Task 1 — wiring fix** |

### 2. The Task Dependencies Are Clear

The swarm split from `ML_SWARM_PROMPT.md` is correct, but the dependencies need strict sequencing:

```
Phase 1 (Day 1, PARALLEL):
  ├── Agent A (CMC): Task 1 (fear_greed injection) + Task 2 (cache verification)
  └── Agent B (Data): Task 3 (fetch 149 tokens × 6 months OHLCV)

Phase 2 (Day 2, SEQUENTIAL after B):
  ├── Agent C (Training): Task 4 (build matrix → train → verify AUC ≥ 0.65)
  └── Agent D (Dashboard): Task 5 (ML audit display — can start with mock data)

Phase 3 (Day 3):
  └── Integration test, artifact promotion, code freeze
```

**Critical path:** Agent B → Agent C. If the data fetch fails or the model doesn't train to AUC ≥ 0.65, the whole chain stops. But the system is **fail-closed** — the bot still works in rule-based mode.

### 3. What the Swarm Can Borrow from Other Repos

| Repo | What to Borrow | Which Agent | Time |
|------|---------------|-------------|------|
| **Qlib** | Vectorized composite labeling (`src/ml/labels.py`) | Agent C | Already done |
| **Qlib** | Purged cross-validation (`src/ml/cv.py` exists) | Agent C | Already done |
| **Freqtrade** | `fetch_ohlcv` rate-limit handling | Agent B | Adapt existing `binance_client.py` |
| **TradingAgents** | Multi-agent reasoning for **demo only** | Agent D | 1 hour — show LLM agents debating a trade in the demo video |
| **FinRL** | Feature standardization pipeline | Agent C | Use `StandardScaler` already in `train.py` |

**Do NOT try to integrate:** XGBoost, CatBoost, or deep RL frameworks. The existing LogReg + LightGBM pipeline is sufficient. The `RegimePredictor` already supports CatBoost but the artifact is LightGBM. Adding a second framework now introduces dependency risk.

### 4. Realistic Time Estimates

| Task | Agent | Best Case | Likely | Worst Case | Risk |
|------|-------|-----------|--------|------------|------|
| Task 1: Fear/greed injection | A | 1h | 2h | 4h | Low — code is straightforward |
| Task 2: Cache verification | A | 30m | 1h | 2h | Low — migration already exists |
| Task 3: Fetch 149 tokens | B | 4h | 8h | 16h | **High** — Binance rate limits, 404s, network |
| Task 4: Train model | C | 2h | 4h | 8h | **High** — AUC may stay < 0.65 |
| Task 5: Dashboard | D | 2h | 3h | 5h | Low — mostly UI work |

**Total critical path:** ~17 hours. With 3 days, that's 5-6 hours per day — achievable if focused.

### 5. The Critical Risk: Task 3 (Data Fetching)

Agent B must fetch 6 months of 15m OHLCV for ~134 non-stablecoin tokens from the eligible list. This is ~2.3M candles.

**Binance constraints:**
- Klines API: weight=1 per request, 1200 weight/minute limit
- Max 1000 candles per request
- 6 months of 15m = ~17,000 candles per token = ~17 requests per token
- 134 tokens × 17 requests = ~2,300 requests
- At 1200/min: minimum 2 minutes. With overhead, retries, 404s: **30-60 minutes**

**The real risk:** Many of the 149 eligible tokens are **not listed on Binance** (e.g., `币安人生`, `WLFI`, `H`, `M`, `B`, `U`). The script must handle 404s gracefully and skip them. The actual number of fetchable tokens might be 60-80, not 134. This reduces the dataset size but might actually improve signal quality (only liquid majors).

**Mitigation:**
- Agent B should start TODAY and run overnight.
- Use a manifest file to resume after crashes.
- Skip stablecoins, gold-backed, and known 404s immediately.
- If < 50 tokens are fetchable, still proceed — 50 tokens × 6 months is plenty for regime detection.

### 6. The Critical Risk: Task 4 (Model Training)

The existing model has AUC 0.58. With real historical data, the target is AUC ≥ 0.65. This is **not guaranteed**.

**What happens if AUC < 0.65?**
- The `MLBundle.is_ranking_active` returns `False` (line 75 in `bundle.py`)
- The system falls back to `is_regime_only_fallback = True` (line 78)
- Position sizing is still modulated by regime (momentum = 1.0x, chop = 0.5x, risk_off = 0.1x)
- **The bot still trades. The rule engine still works.** The ML layer just doesn't get advisory influence.

This is **acceptable for the hackathon**. The judges will see the ML infrastructure, the dashboard, the shadow logging, and the regime-based sizing. They won't see the model fail because it fails silently and safely.

### 7. Can Agent Swarm Prompts Help With Decision-Making?

The user asked about using "agent swarm prompts" for the trading decisions themselves. This is a **different question** from the ML swarm.

**Option A: LLM Trading Agent Swarm (NOT recommended for live trading)**
- Multiple LLM agents debate each trade (technical, sentiment, risk, macro)
- They vote and the majority wins
- This is what TradingAgents (25K⭐) does

**Why it's a bad idea for this competition:**
- LLM latency: 2-5 seconds per agent × 4 agents = 8-20 seconds per decision. The breakout window is 15m candles. Missing a 2% pump by 20 seconds is disqualifying.
- LLM non-determinism: The same setup can give different decisions each time. This breaks reproducibility and backtesting.
- Cost: OpenAI API calls at $0.01-0.03 per 1K tokens. 4 agents × 500 tokens × 288 cycles/day × 7 days = ~$40-120. The x402 budget is $15.
- No edge: LLMs have no proven alpha in crypto trading. They excel at reasoning, not pattern recognition in noisy time series.

**Option B: LLM Agent Swarm for Demo/Presentation (RECOMMENDED)**
- Build a 3-minute demo showing 4 "agents" debating a trade
- Each agent is a different LLM prompt with a persona (Technical Analyst, Sentiment Analyst, Risk Manager, Macro Strategist)
- They vote, the Risk Manager has veto power
- The final decision goes to the rule engine
- This is **purely for the demo video** and scores highly on "originality"
- It does NOT touch live trades. The rule engine makes the actual decision.

**Option C: Multi-Agent Consensus as Shadow (MEDIUM risk)**
- Run the LLM swarm in shadow mode, logging their votes to `decision_shadow.jsonl`
- Compare LLM consensus vs. rule engine vs. actual PnL
- Zero capital risk, high demo value
- Requires 1-2 hours to implement a simple prompt-based pipeline

**Recommendation:** Do **Option B** for the demo video and **Option C** if time permits. Do NOT let LLM agents make live trading decisions.

### 8. What About the Sentiment Feature?

The existing sentiment is **good enough for the hackathon**. Here's the assessment:

| Feature | Current Status | Needed for Swarm? |
|---------|---------------|-------------------|
| Fear & Greed Index (CMC) | ✅ Live, feeds `RegimeDetector` | Agent A needs to inject into ML snapshot |
| Global derivatives (funding, OI) | ✅ Live, feeds `RegimeDetector` | Already in MLFeatureCache |
| BSC gas price | ✅ Live, feeds `RegimeDetector` | Not in ML model ( RPC-dependent) |
| Token-specific social sentiment | ❌ Not implemented | Nice-to-have for demo, not critical |
| Token-specific news | ❌ Not implemented | Nice-to-have for demo, not critical |
| On-chain wallet flows | ❌ Not implemented | Too complex for 3 days |

**Agent A's Task 1** will fix the fear/greed injection gap. The rest can wait until post-hackathon.

### 9. The Honest Recommendation

**Deploy the agent swarm with this plan:**

**Today (June 18, 16:30 UTC):**
- [ ] Spawn Agent A immediately: Fix `fear_greed_index` injection in `src/data/cmc_mcp_client.py` + verify `MLFeatureCache` migration.
- [ ] Spawn Agent B immediately: Extend `scripts/fetch_historical_data.py` for 149 tokens, run it. This will take 4-8 hours. Let it run overnight.

**Tomorrow (June 19):**
- [ ] Check Agent B output: How many tokens fetched successfully? If < 50, proceed anyway.
- [ ] Spawn Agent C: Build feature matrix + train. If AUC < 0.65, try filtering to top 20 liquid tokens. If still < 0.65, accept regime-only fallback.
- [ ] Spawn Agent D: Dashboard ML audit display (can use mock data until C completes).

**June 20:**
- [ ] Integration test. Verify `ml_enabled=true` path works and `ml_enabled=false` path is unchanged.
- [ ] Record demo video. Include the LLM agent debate scene (Option B).
- [ ] Code freeze.

**Hedge plan:** If Agent B fails (data fetch impossible) or Agent C fails (AUC < 0.65), the bot is still fully competitive. The rule engine + sentiment + TWAK + x402 + dashboard is a strong submission. The ML layer becomes a "shadow infrastructure" demo that impresses judges with its architecture even if the model is not yet activated.

### 10. What "Done" Looks Like

| Scenario | ML Ranking Active | Regime Fallback | Dashboard | Demo | Hackathon Score |
|----------|-------------------|-----------------|-----------|------|-----------------|
| **Best case** | ✅ AUC ≥ 0.65 | ✅ Active | ✅ ML audit | ✅ Agents + trades | Very high |
| **Likely case** | ❌ AUC < 0.65 | ✅ Active | ✅ ML audit | ✅ Agents + trades | High |
| **Worst case** | ❌ No data | ✅ Rule-based | ✅ Basic | ✅ Trades only | Medium-high |

**Bottom line:** The swarm can finish the ML layer. The critical path is Agent B (data fetch). If that completes, the rest is downhill. If it fails, the system is still viable. The risk is asymmetric — upside is high, downside is zero.

**Deploy the swarm.**
