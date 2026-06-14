# Codex task — fix the broken SELL path (agent can buy but never sells)

Paste this as the first message of a fresh Codex session with the `cascade-ai`
repo open. The repo lives on EC2 at `/home/ec2-user/nnyb` (the dir
`/home/ec2-user/cascade-ai` is a symlink to it); the live process is the systemd
unit `cascade-ai.service` running `python -m src.main --live`. Python 3.12, venv
at `.venv`. Do NOT redesign the TWAK/execution layer — this is a narrow, surgical
bug fix.

## The bug (competition-blocking)

This is a live spot-trading agent (BNB Chain, BEP-20, via the Trust Wallet Agent
Kit "TWAK" CLI → LiquidMesh router). It enters a live PnL competition June 22–28.

**The agent can BUY but has never successfully SOLD.** Every `entry` (USDC→token)
swap in `execution_log.jsonl` succeeds with a real tx hash. Every `exit` /
`emergency_liquidation` (token→USDC) swap fails. An agent that cannot sell cannot
realize PnL, take profit, or stop losses — it must be fixed before June 22.

### Evidence — a SUCCESSFUL buy (for contrast)
```json
{"action":"entry","from_symbol":"USDC","to_symbol":"AAVE","amount_in":0.39489,
 "result":{"returncode":0,"provider":"LiquidMesh",
 "stderr":"Swapping ... USDC -> ... AAVE via LiquidMesh\nSending token approval...\nApproval tx: 0xf34c...\nSwap tx: 0x5dfe...\nSwap executed!",
 "tx_hash":"0x5dfe2b23e32403a38a053d0f69600cfeef0b93795c8e74d886d33d7212009961"}}
```

### Evidence — a FAILING sell (NOT dust: 231 CAKE ≈ $290)
```json
{"action":"emergency_liquidation","from_symbol":"CAKE","to_symbol":"USDC","amount_in":231.48,
 "error":"twak swap 231.48 failed with exit code 1: stderr: Swapping 231.48 CAKE -> 290.69 USDC via LiquidMesh\nSending token approval...\nApproval tx: https://bscscan.com/tx/0x741a26...| stdout: {\n  \"error\": \"execution reverted: 0xf4059071. Approval was sent (tx: 0x741a26...). Check allowance before retrying.\",\n  \"errorCode\": \"APPROVAL_SENT_SWAP_FAILED\"\n}"}
```
The same `0xf4059071` revert also occurs on tiny dust sells (e.g. 0.0528 ATOM).
So **size is not the cause** — the sell path itself is broken.

## Root-cause hypothesis (verify, don't assume)

When selling an ERC-20, the TWAK CLI does it in one shot: it **sends the token
approval transaction, then immediately attempts the swap in the same invocation**.
The swap reverts (`0xf4059071`) because the approval is not yet mined/effective
when the swap executes. The CLI returns `errorCode: "APPROVAL_SENT_SWAP_FAILED"`
and literally says **"Approval was sent. Check allowance before retrying."** —
i.e. a retry once the allowance is confirmed should succeed. Buys don't hit this
because the approval+swap timing happens to work for USDC, or USDC was already
approved.

First, confirm the mechanism: inspect `twak swap --help` / `twak --help` for an
approval-wait flag, a separate `twak approve` command, or a `--wait`/confirmation
option. Prefer the CLI's own mechanism if one exists.

## Where the code is

- `src/execution/twak_interface.py` → `TWAKInterface.swap()` builds and runs the
  `twak swap <amount> <from> <to> --slippage ... --chain bsc --json` command via
  `_run()`. `_run()` raises `RuntimeError` on any non-zero exit code (it does not
  parse the JSON error payload).
- `src/execution/swap_router.py` → `PancakeSwapRouter.swap_exact_in()` calls
  `twak_interface.swap(...)`.
- Callers: `src/main.py` `_execute_position_exit()` and `emergency_liquidate()`
  (exit/sell path). Note: `_execute_position_exit` was recently hardened to catch
  swap exceptions so a failure no longer crashes the agent — keep that behavior.

## Required fix

Make the **sell path resilient to the approval race** so a token→USDC swap
actually completes:

1. In `TWAKInterface.swap()` (live path only — leave the `paper_trade` branch
   untouched), detect the recoverable approval-race failure: the error payload
   has `errorCode == "APPROVAL_SENT_SWAP_FAILED"` (and/or the revert selector
   `0xf4059071` together with an "Approval was sent" message).
2. On that specific failure, **wait for the allowance to become effective and
   retry the swap**. Implementation options, in order of preference:
   a. If the TWAK CLI exposes an approval-wait / confirmation flag or a separate
      `twak approve` step, use it (approve → confirm → swap).
   b. Otherwise, retry the `twak swap` command up to N times with a bounded
      backoff (e.g. 3 attempts, ~5–10s between, configurable), since the approval
      tx is already broadcast and just needs to be mined.
3. Only retry on the recoverable approval case. Do NOT blanket-retry every
   failure — other reverts may be genuine (insufficient liquidity, slippage,
   real dust below router minimums). Distinguish dust/economically-unswappable
   failures and surface them clearly instead of looping.
4. Make retry count and backoff configurable via settings/env
   (e.g. `SWAP_APPROVAL_RETRY_MAX`, `SWAP_APPROVAL_RETRY_DELAY_SECONDS`) with safe
   defaults; thread them through `src/config/settings.py` like existing settings.
5. Idempotency/safety: a reverted swap moved no tokens, so retrying the swap is
   safe. Be certain you only retry when the swap definitively failed (not when
   state is ambiguous). Never retry a swap that may have partially executed.

## Constraints

- Surgical change. Do not redesign the TWAK integration, the spend governor, the
  x402 flow, or any persisted/frozen schemas.
- Preserve the `paper_trade` short-circuit and the existing exception-catch in
  `_execute_position_exit` (a failed sell must still never crash the agent).
- Keep buys working unchanged.

## Tests (required)

Add unit tests under `tests/` (mock `TWAKInterface._run` / `subprocess`):
- First sell attempt returns `APPROVAL_SENT_SWAP_FAILED`; second attempt returns
  a success payload with a tx hash → `swap()` returns success (retry worked).
- A genuine non-recoverable failure (e.g. liquidity/slippage revert, no
  "approval was sent") is NOT retried and propagates as before.
- The `paper_trade` path is unchanged.
- Retry count/backoff respect the configured limits (mock sleep; assert call
  counts; keep tests fast — no real sleeping).

Run the full suite (`python -m pytest -q`); it should stay green (~353 passing,
the 2 sklearn-version ML warnings are pre-existing).

## Acceptance criteria

1. A token→USDC sell that previously failed with `APPROVAL_SENT_SWAP_FAILED` now
   completes on retry and returns a real tx hash.
2. Buys are unaffected; the agent never crashes on a sell failure.
3. New + existing tests pass.
4. Provide a short note on how to validate live on the box, e.g.:
   `sudo systemctl stop cascade-ai && python -m src.main --emergency-liquidate`
   should now produce a successful `Swap executed!` / tx hash for a non-dust
   position (then `sudo systemctl start cascade-ai`).

## Deliverables

- The code change (twak_interface.py + settings wiring).
- New tests.
- A one-paragraph summary of the confirmed root cause and exactly what you changed.
