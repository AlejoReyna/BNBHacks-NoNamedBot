# Chat API Migration Guide

## What changed

- `src/deployment/chat_api.py` was rewritten from a static rule-based engine to a **Kimi (Moonshot AI) LLM-powered backend**.
- The frontend (`static/chat.html`) and HTTP routes (`/`, `/chat`, `/api/chat`) remain **unchanged**.
- `build_chat_reply()` now accepts an optional `session_id` for multi-turn memory.

## New dependencies

- `openai>=1.30.0` (added to `requirements.txt`)

## Environment variables

Add these to your `.env`:

```bash
# Moonshot AI (Kimi) API — https://platform.moonshot.cn/
KIMI_API_KEY=sk-...
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-8k
```

## How to get a Kimi API key

1. Go to [https://platform.moonshot.cn](https://platform.moonshot.cn) and sign up.
2. Create an API key in the dashboard.
3. Copy the key into your `.env` as `KIMI_API_KEY`.
4. The default `KIMI_BASE_URL` and `KIMI_MODEL` work out of the box.

## How to test

### Direct module test
```bash
python3 scripts/test_chat_api.py
```

### HTTP integration test (spins up the server)
```bash
python3 scripts/test_chat_integration.py
```

### Existing regression suite
```bash
pytest -q
```

## Fallback behavior

- If `KIMI_API_KEY` is **missing**, the chat falls back to the legacy rule-based replies for known keywords (`health`, `status`, `fear`, `greed`, `funding`, `dominance`, `decision`, `trade`, `x402`, `payment`) and shows a friendly error for unknown queries.
- If the **Kimi API is unreachable**, the same keyword-based fallback is used.
- All data sources are gracefully handled: missing files produce `[No data yet]` in the context instead of crashing.

## Multi-turn memory

Pass `session_id` in the JSON body of `POST /api/chat` to maintain conversation history across requests:

```json
{"message": "What is the bot status?", "session_id": "user-42"}
```

The server keeps the last 6 messages (3 user + 3 assistant turns) per session in memory.
