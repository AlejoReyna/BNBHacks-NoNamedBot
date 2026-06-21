"""Direct module test for the Kimi chat backend.

Loads .env and calls build_chat_reply() directly.
Exit 0 if both replies contain non-empty strings, else 1.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

from src.deployment.chat_api import build_chat_reply  # noqa: E402


def main() -> int:
    print("--- Test 1: bot status ---")
    r1 = build_chat_reply("What is the bot status?")
    print(r1)

    print("\n--- Test 2: x402 payment ---")
    r2 = build_chat_reply("Explain the last x402 payment.")
    print(r2)

    ok = bool(r1.get("reply", "").strip()) and bool(r2.get("reply", "").strip())
    if ok:
        print("\n✅ PASS")
        return 0
    print("\n❌ FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
