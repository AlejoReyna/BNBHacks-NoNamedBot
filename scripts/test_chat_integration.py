"""HTTP integration test for the chat endpoint.

Starts the health server on a random port and exercises multi-turn
memory via POST /api/chat.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.deployment.health_state import HealthState  # noqa: E402
from src.deployment.health_server import start_health_server  # noqa: E402


def _post_chat(port: int, message: str, session_id: str) -> dict:
    body = json.dumps({"message": message, "session_id": session_id}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    state = HealthState()
    state.update(status="ok", positions=1, daily_trades=2, drawdown_pct=1.5)
    port = 18080
    server = start_health_server(state, host="127.0.0.1", port=port, decision_log_path="decision_log.jsonl")
    try:
        # Give the server a moment to bind
        time.sleep(0.3)

        print("--- Test 1: Basic chat ---")
        r1 = _post_chat(port, "Hello", "test-123")
        assert "reply" in r1, f"Missing 'reply' in response: {r1}"
        print(f"reply: {r1['reply'][:120]}...")
        print(f"source: {r1.get('source')}")

        print("\n--- Test 2: Multi-turn memory ---")
        r2 = _post_chat(port, "What did I just ask?", "test-123")
        assert "reply" in r2, f"Missing 'reply' in response: {r2}"
        print(f"reply: {r2['reply'][:120]}...")
        print(f"source: {r2.get('source')}")

        print("\n✅ PASS")
        return 0
    except Exception as exc:
        print(f"\n❌ FAIL: {exc}")
        return 1
    finally:
        server.shutdown()


if __name__ == "__main__":
    sys.exit(main())
