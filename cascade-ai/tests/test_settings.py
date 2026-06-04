"""Tests for environment-backed settings."""

from __future__ import annotations

from pathlib import Path

from src.config.settings import load_settings


def test_load_settings_reads_opbnb_provider_url(monkeypatch: object, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPBNB_PROVIDER_URL=https://opbnb.example\n", encoding="utf-8")
    monkeypatch.delenv("OPBNB_PROVIDER_URL", raising=False)  # type: ignore[attr-defined]

    settings = load_settings(str(env_path))

    assert settings.opbnb_provider_url == "https://opbnb.example"


def test_load_settings_defaults_opbnb_provider_url(monkeypatch: object, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("", encoding="utf-8")
    monkeypatch.delenv("OPBNB_PROVIDER_URL", raising=False)  # type: ignore[attr-defined]

    settings = load_settings(str(env_path))

    assert settings.opbnb_provider_url == "https://opbnb-mainnet-rpc.bnbchain.org"
