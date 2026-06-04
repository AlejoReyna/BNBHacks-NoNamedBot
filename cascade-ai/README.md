# Plan B+ — BSC Momentum Breakout Scalper

Plan B+ is a runnable Python skeleton for the BNB Hack: AI Trading Agent Edition, Track 1. It is an autonomous, rule-based BSC momentum breakout scalper for high-volume BNB Chain tokens with strict guardrails, local TWAK signing, and x402 access to CoinMarketCap premium data.

It intentionally does not include ML, external inference servers, invented trading APIs, cloud workers, VPS setup, or fake PancakeSwap SDKs.

## Architecture

- `src/data`: CoinMarketCap MCP JSON-RPC calls and x402 payment retry handling.
- `src/execution`: TWAK subprocess commands, bnb-chain-agentkit balance/transfer wrapper, and PancakeSwap V3 conceptual routing through TWAK swap execution.
- `src/strategy`: six-factor breakout scoring, JSON-backed position tracking, and executable guardrails.
- `src/config`: settings, token allowlists, and environment-only secret access.
- `src/main.py`: CLI entrypoint and 5-minute trading loop.

## Verified Tools

CMC MCP tool names used exactly:

- `get_crypto_quotes_latest`
- `get_crypto_technical_analysis`
- `get_global_crypto_derivatives_metrics`
- `get_crypto_market_metrics`

Official x402 endpoint:

```text
https://mcp.coinmarketcap.com/x402/mcp
```

Verified execution imports:

```python
from bnb_chain_agentkit.agent_toolkits import BnbChainToolkit
from bnb_chain_agentkit.utils import BnbChainAPIWrapper
```

Verified TWAK commands:

```bash
twak wallet create
twak compete register
twak x402 request <endpoint> --method POST --body <json> --max-payment <atomic> --prefer-asset <token> --yes --json
twak swap --from <token> --to <token> --amount <amount> --slippage <pct> --chain BSC --mode agent --broadcast
twak start
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure `.env` with real CMC access, RPC URLs, wallet address, token addresses, and TWAK setup before live trading.
The current `bnb-chain-agentkit` package requires Python 3.12+ and
`BSC_PROVIDER_URL`/`BSC_RPC_URL` for live balance and transfer operations.

## TWAK Setup

```bash
twak wallet create
twak compete register
```

## Run

Paper mode:

```bash
python -m src.main --paper-trade
```

Live mode:

```bash
python -m src.main --live
```

Emergency liquidation:

```bash
python -m src.main --emergency-liquidate
```

Emergency liquidation defaults to live execution and loads `POSITION_STATE_PATH`
before selling open positions back to USDC. Use `--paper-trade` with the
emergency command only for a dry run.

Tests:

```bash
pytest
```

## Strategy

The agent evaluates the focused 20-token target universe every 5 minutes. USDT and USDC remain configured for routing and balance checks, but are excluded from directional entries. It enters a spot long on the tradable subset when at least 4 of 6 factors are true:

- 1h volume is greater than 2x rolling 24h hourly average.
- Price breaks the 6h high.
- BNB 1h trend is not sharply risk-off.
- RSI is between 55 and 75, inclusive.
- Estimated slippage is under 1%.
- Funding and open interest are not flashing broad liquidation risk.

After entry, the position manager persists the open position, sets a trailing stop 3.5% below entry, and sets a fixed take-profit at +8%.

## Risk Guardrails

- Strict trading allowlist: only `TRADABLE_TARGET_SYMBOLS` for directional entries; stables are base/settlement tokens only.
- Max position size: 5% of portfolio per trade.
- Max daily trades: 3.
- Max daily realized loss: 3% of portfolio, then pause entries for 24 hours.
- Max swap slippage: 1%.
- Drawdown kill switch: 20% from all-time high triggers liquidation to USDC and terminates the loop.
- Manual emergency command loads persisted positions or reconstructs target-token wallet balances, then sells non-USDC positions to USDC without undocumented TWAK commands.

The June 22-28 live-window trade target is implemented only as a log warning. Guardrails are never overridden to force a trade.

## Live Trading Notes

Real trading requires funded wallets, correct BSC and opBNB RPC configuration, token addresses, TWAK setup, CMC/x402 access, and installed dependencies. This skeleton persists positions to `positions.json` and guardrails to `guardrail_state.json` by default; production deployments should still harden state recovery and reconciliation before running unattended capital.
