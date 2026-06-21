# Demo Video Script — Cascade AI / NoNamedYet_Bot

**Target:** 3:00 · **Optimized for:** "Best Use of Trust Wallet Agent Kit" special prize (Track 1)
**Also covers:** the discretionary panel's four general criteria (technical execution, originality, real-world relevance, demo)

> **How to read this script:** the lines marked **ACCIÓN** (in Spanish) are what *you* do on screen — switch views, open files, run commands. The **VO** lines are what you say out loud (in English, for the recording). The **Caption** is the on-screen lower third.

> **Submission note:** DoraHacks BUIDL deadline is 2026-06-21 06:00 UTC. The video, the public repo, and the on-chain agent address must all be in the submission. Show at least one BSC tx hash on screen — it is an explicit submission requirement and worth points under both the demo criterion and the TWAK breakdown.

---

## How this script maps to the scoring

The TWAK special prize is scored on six weighted lines. Every segment below is built to earn specific points, not to fill time.

| TWAK scoring line | Weight | Where it's earned in this video |
| --- | --- | --- |
| TWAK integration depth | 30 | 0:25–1:10 (sole execution layer, 4+ CLI surfaces) |
| Self-custody integrity | 25 | 0:25–0:50 (no key in Python, keychain unlock, subprocess signing) |
| Autonomous execution + guardrails | 20 | 1:10–2:05 (5-min loop, fail-closed risk controls) |
| Native x402 usage | 10 | 2:05–2:30 (pay-per-request CMC data inside the loop) |
| Originality + real-world relevance | 10 | 0:10–0:25, 2:30–2:45 (LLM read-only market-intel chat), 2:45–2:52 (25%-of-AUM budget model, unattended self-custody user) |
| Demo + presentation | 5 | throughout + 2:45–3:00 (on-chain proof close) |

Lower thirds / captions should name the scoring line being demonstrated so a judge scoring against the rubric can tick boxes in real time.

---

## Cold open — 0:00–0:10 · The one-line thesis

**ACCIÓN:** Empieza con una tarjeta negra. Luego **cambia a la vista del terminal** con el agente a mitad de ciclo y, justo después, **cambia a la pestaña de BscScan** con la transacción del swap.

**VO:**
> "This is a self-custody trading agent for BNB Chain. It reads the market through CoinMarketCap, decides on its own, and signs every transaction itself through Trust Wallet Agent Kit — with no private key ever living in the Python process."

**Caption:** `CMC reads → agent decides → TWAK signs · keys never leave the user`

*Why it scores:* states the exact thesis the TWAK prize rewards — "the heart of a genuinely hands-off trader, not plumbing bolted onto an LLM."

---

## 0:10–0:25 · Why it exists (originality + real-world relevance, 10)

**ACCIÓN:** **Cambia a la vista del README** y desplázate hasta la sección "Budget Model: 25% of AUM for Data". Haz un destello rápido del archivo `src/data/x402_optimizer.py`.

**VO:**
> "Most agents bolt an LLM onto a swap call. We built it the other way around: a deterministic strategy core, an institutional data-budget model that scales intelligence spend with capital, and self-custody as a hard requirement — an agent a real user would actually leave running unattended."

**Caption:** `Deterministic core · 25% AUM data budget · built to run unattended`

*Why it scores:* directly answers "a new take on an agent a self-custody user would actually let run unattended, with a clear user and a plausible path to adoption."

---

## 0:25–0:50 · Self-custody integrity (25)

**ACCIÓN:** **Cambia a una vista dividida (split screen):** a la izquierda, **abre el archivo** `src/execution/twak_interface.py` y resalta la llamada al subproceso del CLI `twak`. A la derecha, **abre el terminal y ejecuta:**

```bash
twak wallet keychain check
twak wallet address --chain bsc --json
```

**VO:**
> "Here's the core claim, on screen. Python never holds a trading key. Every signature is produced by the TWAK CLI as a subprocess, and the wallet is unlocked from the OS keychain — not from a file, not from an environment secret in the trade path. Signing authority stays with the user through the entire loop."

**Caption:** `No private key in Python · keychain unlock · local signing end-to-end → self-custody 25`

*Why it scores:* this is the 25-point line, and the penalty ladder gives 20–25 only for "fully self-custodial, clean local signing." Showing the subprocess boundary on screen is the proof.

---

## 0:50–1:10 · TWAK integration depth (30)

**ACCIÓN:** **Cambia a la vista del terminal a pantalla completa** y muestra, en montaje rápido, cada una de las superficies de TWAK que el agente usa de verdad (puedes mostrarlas como comandos ya ejecutados):

```bash
twak compete register                       # on-chain competition registration
twak wallet address --chain bsc --json      # identity
twak swap 0.5 USDC BNB --slippage 1 --chain bsc --quote-only --json   # pre-trade safety quote
twak swap 0.5 USDC BNB --slippage 1 --chain bsc --json                # live signed swap
```

**VO:**
> "TWAK is the only thing that touches the chain here. It's not a single swap call — the agent leans on multiple surfaces: on-chain competition registration, wallet identity, quote-only slippage checks before it commits, and signed execution. If you removed TWAK, there is no execution layer left."

**Caption:** `Sole execution layer · register + identity + quote + signed swap → TWAK depth 30`

*Why it scores:* the 30-point line rewards "TWAK is the sole execution layer, and the agent leans on more than one surface... not a single swap call with the real logic living elsewhere." Tie-breaker also favors "deepest, least-replaceable TWAK integration."

---

## 1:10–1:35 · The autonomous loop (autonomy + guardrails, 20 — part 1)

**ACCIÓN:** **Cambia a la vista del terminal** y **ejecuta el agente en vivo:**

```bash
python -m src.main --live --demo-mode
```

Deja que el resumen por ciclo vaya apareciendo. **Superpón (overlay) el diagrama del loop** del README (Fetch CMC → regime → score → guardrails → TWAK swap → reconcile).

**VO:**
> "Live, this runs every five minutes with no human in the loop. Each cycle it pulls a CoinMarketCap snapshot, detects the market regime, scores the token universe zero to one hundred with a rule-based momentum-breakout model, and only then decides: enter or wait. When it enters, it signs its own transaction."

**Caption:** `5-min loop · regime-aware breakout scoring · signs its own tx → hands-off`

*Why it scores:* "the agent signs and processes its own transactions, genuinely hands-off."

---

## 1:35–2:05 · Guardrails (autonomy + guardrails, 20 — part 2)

**ACCIÓN:** **Cambia a la vista del terminal** y **ejecuta** para mostrar los logs estructurados; luego **señala con el cursor** las líneas concretas:

```bash
tail logs/decision_live.jsonl     # action: ENTER / WAIT / BLOCKED / HALT
tail logs/risk_events.jsonl       # kill switch, pause, limit breaches
```

Muestra una decisión `BLOCKED` y un rechazo por slippage del paso quote-only.

**VO:**
> "Hands-off only works if the rules are real. Entries are fail-closed: a one-percent max slippage cap, a token allowlist, three trades a day, a three-percent daily-loss pause, and a fifteen-percent drawdown kill switch that liquidates and halts. Here's a blocked entry, and here's a trade the slippage check stopped before any capital moved. Guardrails are never bypassed — not even for the competition window."

**Caption:** `Slippage 1% · allowlist · 3 trades/day · 3% daily-loss pause · 15% kill switch`

*Why it scores:* names every guardrail the rubric lists explicitly — "drawdown caps, token allowlists, per-trade and daily limits, slippage protection."

---

## 2:05–2:30 · Native x402 (10)

**ACCIÓN:** **Cambia a la vista del terminal** y **ejecuta en vivo una petición pagada de verdad:**

```bash
python scripts/smoke_cmc_x402_paid_quote.py
```

Deja que se vea la respuesta de la quote pagada. Luego **abre el código** que construye el payload x402 (`src/data/x402_payment.py`) y **muestra el spend governor** (`src/data/x402_spend_governor.py`, el límite de gasto). Para cerrar, **cambia a la vista del agente en vivo** y señala una línea de enrichment x402 dentro del loop.

**VO:**
> "Data isn't free, so the agent pays for it the agent-native way. Inside the trade loop it uses x402 to pay per request for premium CoinMarketCap enrichment — real micropayments on Base, settled from an ephemeral signer that's deliberately isolated from the trading wallet, and bounded by a spend governor so it can't overspend the data budget. This is x402 doing actual work in the loop, live, not a line in a README."

**Caption:** `x402 pay-per-request CMC data · isolated signer · spend governor → x402 10`

*Why it scores:* the 10-point line requires "x402 to pay per request for data, inference, or tools as part of its trade loop. Real, not a README mention." Showing a live paid quote plus the isolated signer and spend governor earns the full points and reinforces self-custody hygiene.

---

## 2:30–2:45 · LLM market-intel layer + real-world framing (relevance, reinforces 10)

**ACCIÓN:** **Cambia a la vista del dashboard** (la consola de operador read-only). **Abre el panel de Market Intel chat** y **escribe una pregunta en lenguaje natural**, por ejemplo: *"¿por qué el agente está en WAIT ahora mismo?"* o *"resume las últimas decisiones y el drawdown actual"*. Deja que la respuesta del LLM se escriba en pantalla con el efecto typewriter.

**VO:**
> "One more layer: a natural-language market-intel chat, powered by an LLM — Kimi or OpenAI, server-side. But notice where it lives. The trading decisions are deterministic and rule-based; the LLM never signs, never executes, never touches a key. It's a read-only analyst on top of live telemetry — so you can ask the agent why it's waiting, and still trust that nothing it says can move your funds. The execution loop is the heart, not the LLM."

**Caption:** `LLM market-intel chat · read-only · never in the signing path → rules execute, LLM explains`

*Why it scores:* turns a potential weakness into a strength — the rubric explicitly rewards TWAK "as the heart of a genuinely hands-off trader, **not plumbing bolted onto an LLM**." Showing the LLM as an isolated, read-only explainer proves the execution core is deterministic and self-custodial, while still demonstrating an inventive, user-facing feature (originality + relevance).

---

## 2:45–2:52 · Honest economics (relevance)

**ACCIÓN:** **Cambia a la vista del README** y muestra brevemente la tabla "Known Limitations" / "Budget Model".

**VO:**
> "And we're honest about where this lives: structurally it's a fund tool — minimum viable capital is a few thousand dollars, where the data budget pays for itself. The real user is someone who wants an unattended, self-custody quant agent and won't hand over their keys to do it."

**Caption:** `Clear user · honest economics · self-custody as the product, not a feature`

*Why it scores:* "a clear user and a plausible path to adoption," and signals technical maturity to the panel.

---

## 2:52–3:00 · On-chain proof close (demo, 5 + submission requirement)

**ACCIÓN:** **Cambia a la pestaña de BscScan** con el swap real y mantén la vista fija el tiempo suficiente para leer los hashes. Después **cambia a la vista del contrato de la competición.**

- Agent wallet: `0x7CE28f5d2D1B2eFd8f87FF0a7fdC7D2EaB465c9c`
- Swap tx: `0x2b5db498c97d6c69af6718872feb749457e7e6434c17569a34a2f78ff64eda94`
- Approval tx: `0x5863c33ba5fbfd7016fae9dfe062d853213b198376862fd76ce81336a20fe7d0`
- Competition contract: `0x212c61b9b72c95d95bf29cf032f5e5635629aed5`

**VO:**
> "And it's real on-chain. This is a TWAK-signed swap on BSC — half a USDC into BNB through LiquidMesh, zero price impact, signed locally by the agent. Same wallet, registered on the competition contract. CoinMarketCap for sight, Trust Wallet Agent Kit for hands, your keys the whole way. That's the agent."

**Caption:** `Live BSC proof · TWAK-signed · self-custody loop, end to end`

*Why it scores:* the demo criterion wants the self-custody and autonomous-signing loop "end to end, backed by on-chain proof (contract address or tx hash on BSC)." This closes both the special-prize demo line and the general submission requirement.

---

## Production checklist

**Antes de grabar — capturar primero (para no falsear nada en vivo):**

- [ ] `twak wallet keychain check` devuelve OK en cámara
- [ ] `python -m src.main --live --preflight` pasa (readiness, sin broadcasts)
- [ ] Un ciclo real con `--demo-mode` produce un resumen limpio en stdout
- [ ] `logs/decision_live.jsonl` contiene un `BLOCKED` y un `ENTER` visibles
- [ ] `logs/risk_events.jsonl` tiene al menos un evento de guardrail para señalar
- [ ] `python scripts/smoke_cmc_x402_paid_quote.py` devuelve una quote pagada exitosa en cámara (EC2 con uso diario restaurado)
- [ ] Pestañas de BscScan precargadas con los dos tx hashes + el contrato de la competición

**Higiene en pantalla:**

- [ ] Difumina / borra cualquier contraseña real de wallet, URL de RPC con clave o secretos del `.env`
- [ ] Mantén visible el límite del subproceso `twak` cuando afirmes "no key in Python"
- [ ] Las captions nombran la línea de puntuación para que los jueces la mapeen al rubric
- [ ] Tarjeta final: URL del repo + dirección del agent wallet + "self-custody · CMC · TWAK · x402"

**Ritmo (pacing):** 3:00 va justo. Si te alargas, corta primero de 2:45–2:52 (honest economics); el LLM (2:30–2:45) merece quedarse porque neutraliza el "plumbing bolted onto an LLM". Los puntos clave viven en self-custody (0:25–0:50), TWAK depth (0:50–1:10) y guardrails (1:35–2:05).

---

## General-criteria coverage (for the main Track 1 panel, if shown there too)

| General criterion | Covered by |
| --- | --- |
| Technical execution — "real, not cosmetic" | On-chain swap proof (2:45), live loop (1:10), 440+ passing tests (63 test files) can be flashed |
| Originality | 25%-of-AUM data budget + Lagrangian x402 optimizer (0:10) |
| Real-world relevance | Unattended self-custody user + honest economics (2:30) |
| Demo & presentation | Whole video is the self-custody loop end to end with proof |

> Track 1's main placement is scored on live PnL during June 22–28, not on the video. This video is your vehicle for the **special prizes** (especially Best Use of TWAK) and for the submission's reproducibility requirement.
