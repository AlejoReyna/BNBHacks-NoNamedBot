"""Subprocess interface for the verified Trust Wallet Agent Kit CLI."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TWAKResult:
    """Result returned by a TWAK CLI command."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str


class TWAKInterface:
    """Secure wrapper around documented TWAK commands."""

    def __init__(self, paper_trade: bool = False) -> None:
        self.paper_trade = paper_trade

    def wallet_create(self) -> TWAKResult:
        """Run twak wallet create."""

        return self._run(["twak", "wallet", "create"])

    def compete_register(self) -> TWAKResult:
        """Run twak compete register."""

        return self._run(["twak", "compete", "register"])

    def pay_x402(self, url: str, amount: float, asset: str) -> TWAKResult:
        """Pay an x402 endpoint through TWAK."""

        return self._run(["twak", "x402", "pay", "--url", url, "--amount", str(amount), "--asset", asset])

    def request_x402(
        self,
        url: str,
        method: str,
        json_body: dict[str, Any] | None,
        amount: float,
        asset: str,
    ) -> TWAKResult:
        """Request an x402 endpoint through the current TWAK CLI."""

        command = [
            "twak",
            "x402",
            "request",
            url,
            "--method",
            method.upper(),
            "--max-payment",
            self._amount_to_atomic_units(amount, asset),
            "--prefer-asset",
            asset,
            "--yes",
            "--json",
        ]
        if json_body is not None:
            command.extend(["--body", json.dumps(json_body, separators=(",", ":"))])
        return self._run(command)

    def swap(
        self,
        from_symbol: str,
        to_symbol: str,
        amount: float,
        slippage_pct: float,
    ) -> dict[str, Any]:
        """Execute a swap through TWAK."""

        if amount <= 0:
            raise ValueError("swap amount must be greater than zero")
        if slippage_pct <= 0:
            raise ValueError("swap slippage must be greater than zero")
        if self.paper_trade:
            return {
                "mode": "paper",
                "tool": "twak-swap",
                "from_symbol": from_symbol,
                "to_symbol": to_symbol,
                "amount_in": amount,
                "estimated_amount_out": amount,
                "slippage_pct": slippage_pct,
                "tx_hash": f"paper-twak-swap-{from_symbol.upper()}-{to_symbol.upper()}",
            }

        result = self._run(
            [
                "twak",
                "swap",
                "--from",
                from_symbol,
                "--to",
                to_symbol,
                "--amount",
                str(amount),
                "--slippage",
                str(slippage_pct),
                "--chain",
                "BSC",
                "--mode",
                "agent",
                "--broadcast",
            ]
        )
        return self._swap_payload_from_result(result)

    def start(self) -> TWAKResult:
        """Run twak start."""

        return self._run(["twak", "start"])

    @staticmethod
    def _run(command: list[str]) -> TWAKResult:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                shell=False,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            command_name = " ".join(command[:3])
            raise RuntimeError(f"{command_name} timed out") from exc
        except FileNotFoundError as exc:
            raise RuntimeError("TWAK CLI was not found on PATH") from exc

        result = TWAKResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )
        if result.returncode != 0:
            command_name = " ".join(command[:3])
            message = result.stderr or result.stdout or "<no output>"
            raise RuntimeError(f"{command_name} failed with exit code {result.returncode}: {message}")
        return result

    @staticmethod
    def _amount_to_atomic_units(amount: float, asset: str) -> str:
        normalized = asset.strip().lower()
        six_decimal_assets = {
            "usdc",
            "usdt",
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
        }
        decimals = 6 if normalized in six_decimal_assets else 18
        return str(int(round(amount * (10**decimals))))

    @staticmethod
    def _swap_payload_from_result(result: TWAKResult) -> dict[str, Any]:
        payload: dict[str, Any]
        try:
            decoded = json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            decoded = {"raw": result.stdout}
        payload = decoded if isinstance(decoded, dict) else {"raw": decoded}
        payload.setdefault("mode", "twak")
        payload.setdefault("tool", "swap")
        payload.setdefault("command", result.command)
        payload.setdefault("returncode", result.returncode)
        if result.stderr:
            payload.setdefault("stderr", result.stderr)
        return payload
