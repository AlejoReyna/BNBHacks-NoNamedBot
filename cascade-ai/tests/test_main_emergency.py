"""Tests for emergency liquidation startup behavior."""

from __future__ import annotations

import pytest

from src.config.settings import Settings
from src import main as main_module
from src.strategy.position_manager import PositionManager


def test_emergency_liquidate_defaults_to_live_mode(monkeypatch: object, tmp_path: object) -> None:
    state_path = tmp_path / "positions.json"  # type: ignore[operator]
    guardrail_path = tmp_path / "guardrail_state.json"  # type: ignore[operator]
    settings = Settings(
        paper_trade=True,
        position_state_path=str(state_path),
        guardrail_state_path=str(guardrail_path),
    )
    seeded = PositionManager(settings)
    seeded.open_position("CAKE", amount_tokens=2.0, entry_price=3.0, entry_value_usdc=6.0)
    observed: dict[str, object] = {}

    class FakeToolkit:
        def __init__(self, live_settings: Settings) -> None:
            observed["paper_trade"] = live_settings.paper_trade

    class FakeTWAK:
        def __init__(self, paper_trade: bool = False) -> None:
            observed["twak_paper_trade"] = paper_trade

        def swap(self, from_symbol: str, to_symbol: str, amount: float, slippage_pct: float) -> dict[str, object]:
            observed["swap"] = (from_symbol, to_symbol, amount, slippage_pct)
            return {"amount_out": amount}

    monkeypatch.setattr(main_module, "load_settings", lambda: settings)  # type: ignore[attr-defined]
    monkeypatch.setattr(main_module, "BnbToolkitWrapper", FakeToolkit)  # type: ignore[attr-defined]
    monkeypatch.setattr(main_module, "TWAKInterface", FakeTWAK)  # type: ignore[attr-defined]

    assert main_module.main(["--emergency-liquidate"]) == 0
    assert observed["paper_trade"] is False
    assert observed["twak_paper_trade"] is False
    assert observed["swap"] == ("CAKE", "USDC", 2.0, 0.01)


def test_balance_command_reads_live_balances(monkeypatch: object, capsys: object) -> None:
    settings = Settings(paper_trade=True)
    observed: dict[str, object] = {}

    class FakeToolkit:
        def __init__(self, live_settings: Settings) -> None:
            observed["paper_trade"] = live_settings.paper_trade

        def get_balance(self, symbol: str) -> dict[str, object]:
            return {"balance": {"BNB": 0.001, "USDC": 10.5, "USDT": 0.0}[symbol]}

    monkeypatch.setattr(main_module, "load_settings", lambda: settings)  # type: ignore[attr-defined]
    monkeypatch.setattr(main_module, "BnbToolkitWrapper", FakeToolkit)  # type: ignore[attr-defined]

    assert main_module.main(["--live", "--balance"]) == 0

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert observed["paper_trade"] is False
    assert "BNB: 0.00100000" in output
    assert "USDC: 10.50000000" in output


def test_withdraw_requires_live_mode() -> None:
    with pytest.raises(SystemExit):
        main_module.parse_args(
            [
                "--withdraw",
                "USDC",
                "--to",
                "0x2222222222222222222222222222222222222222",
                "--amount",
                "1",
            ]
        )


def test_withdraw_command_invokes_transfer(monkeypatch: object, capsys: object) -> None:
    settings = Settings(paper_trade=True)
    observed: dict[str, object] = {}

    class FakeToolkit:
        def __init__(self, live_settings: Settings) -> None:
            observed["paper_trade"] = live_settings.paper_trade

        def transfer(self, to_address: str, symbol: str, amount: float) -> dict[str, object]:
            observed["transfer"] = (to_address, symbol, amount)
            return {"tx_hash": "0xabc"}

    monkeypatch.setattr(main_module, "load_settings", lambda: settings)  # type: ignore[attr-defined]
    monkeypatch.setattr(main_module, "BnbToolkitWrapper", FakeToolkit)  # type: ignore[attr-defined]

    assert main_module.main(
        [
            "--live",
            "--withdraw",
            "USDC",
            "--to",
            "0x2222222222222222222222222222222222222222",
            "--amount",
            "1.25",
        ]
    ) == 0

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert observed["paper_trade"] is False
    assert observed["transfer"] == ("0x2222222222222222222222222222222222222222", "USDC", 1.25)
    assert "withdraw_tx_hash=0xabc" in output


def test_once_command_limits_live_run_to_one_cycle(monkeypatch: object) -> None:
    settings = Settings(paper_trade=True)
    observed: dict[str, object] = {}

    def fake_run_agent(live_settings: Settings, max_cycles: int | None = None) -> None:
        observed["paper_trade"] = live_settings.paper_trade
        observed["max_cycles"] = max_cycles

    monkeypatch.setattr(main_module, "load_settings", lambda: settings)  # type: ignore[attr-defined]
    monkeypatch.setattr(main_module, "run_agent", fake_run_agent)  # type: ignore[attr-defined]

    assert main_module.main(["--live", "--once"]) == 0
    assert observed == {"paper_trade": False, "max_cycles": 1}


def test_entry_aborts_before_router_when_slippage_is_missing(tmp_path: object) -> None:
    settings = Settings(
        position_state_path=str(tmp_path / "positions.json"),  # type: ignore[operator]
        guardrail_state_path=str(tmp_path / "guardrail_state.json"),  # type: ignore[operator]
    )
    position_manager = PositionManager(settings)
    guardrails = main_module.Guardrails(settings)
    decision = main_module.BreakoutDecision(
        should_enter=True,
        symbol="CAKE",
        position_size_usdc=100.0,
        factor_scores={"slippage_under_cap": False},
        true_factor_count=5,
        reason="test",
    )

    class FakeRouter:
        calls = 0

        def swap_exact_in(self, *args: object, **kwargs: object) -> dict[str, object]:
            self.calls += 1
            return {}

    router = FakeRouter()

    main_module._maybe_enter_position(
        decision,
        position_manager,
        router,  # type: ignore[arg-type]
        guardrails,
        {"CAKE": {"price": 2.0, "estimated_slippage_pct": None}},
        10000.0,
    )

    assert router.calls == 0
    assert position_manager.get_position("CAKE") is None
