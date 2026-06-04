"""Tests for Trust Wallet Agent Kit CLI command adaptation."""

from __future__ import annotations

from typing import Any

import pytest

from src.execution.twak_interface import TWAKInterface


def test_swap_uses_twak_broadcast_command(monkeypatch: Any) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> object:
        captured["command"] = command
        return type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": '{"amount_out":99.0}',
                "stderr": "",
            },
        )()

    monkeypatch.setattr("subprocess.run", fake_run)

    result = TWAKInterface().swap("USDC", "CAKE", 100.0, 0.01)

    assert result["amount_out"] == 99.0
    assert captured["command"] == [
        "twak",
        "swap",
        "--from",
        "USDC",
        "--to",
        "CAKE",
        "--amount",
        "100.0",
        "--slippage",
        "0.01",
        "--chain",
        "BSC",
        "--mode",
        "agent",
        "--broadcast",
    ]


def test_paper_swap_does_not_broadcast(monkeypatch: Any) -> None:
    def fail_run(command: list[str], **kwargs: object) -> object:
        raise AssertionError("paper swap should not invoke subprocess")

    monkeypatch.setattr("subprocess.run", fail_run)

    result = TWAKInterface(paper_trade=True).swap("USDC", "CAKE", 100.0, 0.01)

    assert result["mode"] == "paper"
    assert result["tool"] == "twak-swap"


def test_request_x402_uses_current_twak_cli_shape(monkeypatch: Any) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str]) -> object:
        captured["command"] = command
        return type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": '{"ok":true}',
                "stderr": "",
            },
        )()

    monkeypatch.setattr("subprocess.run", lambda command, **kwargs: fake_run(command))

    result = TWAKInterface().request_x402(
        "https://mcp.coinmarketcap.com/x402/mcp",
        "POST",
        {"a": 1},
        0.01,
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    )

    assert result.returncode == 0
    assert captured["command"] == [
        "twak",
        "x402",
        "request",
        "https://mcp.coinmarketcap.com/x402/mcp",
        "--method",
        "POST",
        "--max-payment",
        "10000",
        "--prefer-asset",
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "--yes",
        "--json",
        "--body",
        '{"a":1}',
    ]


def test_twak_failure_reports_stdout_when_stderr_is_empty(monkeypatch: Any) -> None:
    def fake_run(command: list[str], **kwargs: object) -> object:
        return type(
            "Completed",
            (),
            {
                "returncode": 1,
                "stdout": '{"error":"PASSWORD_MISSING"}',
                "stderr": "",
            },
        )()

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="PASSWORD_MISSING"):
        TWAKInterface().request_x402(
            "https://mcp.coinmarketcap.com/x402/mcp",
            "POST",
            {"a": 1},
            0.01,
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        )
