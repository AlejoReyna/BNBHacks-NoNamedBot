"""TTL cache for CMC market snapshots independent of the trading loop."""

from __future__ import annotations

import copy
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

DEFAULT_PERSIST_PATH = "logs/market_snapshot_cache.json"

HOT_SNAPSHOT_FIELDS = (
    "price",
    "market_cap",
    "volume_1h",
    "volume_24h",
    "percent_change_1h",
    "percent_change_6h",
    "percent_change_24h",
    "high_3h",
    "high_6h",
    "high_24h",
    "low_24h",
    "rolling_24h_hourly_volume_avg",
    "bnb_1h_trend_pct",
    "estimated_slippage_pct",
)


def merge_market_snapshots(
    base: dict[str, dict[str, Any]],
    overlay: dict[str, dict[str, Any]],
    *,
    hot_fields: tuple[str, ...] = HOT_SNAPSHOT_FIELDS,
) -> dict[str, dict[str, Any]]:
    """Merge keyless hot fields over an x402-enriched base snapshot."""

    merged = copy.deepcopy(base) if base else {}
    for symbol, overlay_data in overlay.items():
        if not isinstance(overlay_data, dict):
            continue
        normalized = str(symbol).upper()
        existing = merged.get(normalized, {})
        if existing:
            combined = copy.deepcopy(existing)
            for field in hot_fields:
                value = overlay_data.get(field)
                if value is not None and value != 0 and value != "":
                    combined[field] = value
            combined["symbol"] = normalized
        else:
            combined = copy.deepcopy(overlay_data)
            combined["symbol"] = normalized
        merged[normalized] = combined
    return merged


class MarketSnapshotCache:
    """Reuse the last CMC snapshot until its TTL expires."""

    def __init__(self) -> None:
        self._snapshot: dict[str, dict[str, Any]] = {}
        self._fetched_at: float = 0.0

    def get_or_fetch(
        self,
        ttl_seconds: int,
        fetcher: Callable[[], dict[str, dict[str, Any]]],
        *,
        force_refresh: bool = False,
    ) -> dict[str, dict[str, Any]]:
        if ttl_seconds <= 0:
            return fetcher()

        now = time.monotonic()
        age = now - self._fetched_at
        if not force_refresh and self._snapshot and age < ttl_seconds:
            LOGGER.debug(
                "Reusing CMC market snapshot (age=%.0fs ttl=%ss symbols=%s)",
                age,
                ttl_seconds,
                len(self._snapshot),
            )
            return copy.deepcopy(self._snapshot)

        snapshot = fetcher()
        self._snapshot = copy.deepcopy(snapshot)
        self._fetched_at = now
        LOGGER.info(
            "Refreshed CMC market snapshot (ttl=%ss symbols=%s)",
            ttl_seconds,
            len(snapshot),
        )
        return copy.deepcopy(snapshot)

    def reset(self) -> None:
        self._snapshot = {}
        self._fetched_at = 0.0


class DualMarketSnapshotCache:
    """Independent TTL layers for x402-enriched and keyless quote snapshots.

    The paid x402 layer is persisted to disk (snapshot + wall-clock
    fetched-at) so process restarts do not trigger a paid refresh while the
    TTL is still fresh. The keyless layer is free and refetches within one
    cycle, so it is not persisted.
    """

    def __init__(self, persist_path: str | Path | None = None) -> None:
        self._x402_enriched: dict[str, dict[str, Any]] = {}
        self._x402_fetched_at: float = 0.0
        self._keyless_quotes: dict[str, dict[str, Any]] = {}
        self._keyless_fetched_at: float = 0.0
        self._persist_path: Path | None = Path(persist_path) if persist_path else None
        self._load_persisted()

    def x402_age_seconds(self) -> float | None:
        """Age of the paid x402 layer, or None when no snapshot exists."""

        if not self._x402_enriched:
            return None
        return max(0.0, time.monotonic() - self._x402_fetched_at)

    def refresh_keyless(
        self,
        ttl_seconds: int,
        fetcher: Callable[[], dict[str, dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        """Refresh (per TTL) and return the free keyless layer."""

        self._maybe_refresh_layer(
            layer_name="keyless",
            snapshot_attr="_keyless_quotes",
            fetched_at_attr="_keyless_fetched_at",
            ttl_seconds=ttl_seconds,
            fetcher=fetcher,
            now=time.monotonic(),
        )
        return copy.deepcopy(self._keyless_quotes)

    def get_merged_snapshot(
        self,
        x402_ttl_seconds: int,
        keyless_ttl_seconds: int,
        x402_fetcher: Callable[[], dict[str, dict[str, Any]]],
        keyless_fetcher: Callable[[], dict[str, dict[str, Any]]],
        *,
        force_x402_refresh: bool = False,
    ) -> dict[str, dict[str, Any]]:
        now = time.monotonic()
        self._maybe_refresh_layer(
            layer_name="x402",
            snapshot_attr="_x402_enriched",
            fetched_at_attr="_x402_fetched_at",
            ttl_seconds=0 if force_x402_refresh else x402_ttl_seconds,
            fetcher=x402_fetcher,
            now=now,
        )
        self._maybe_refresh_layer(
            layer_name="keyless",
            snapshot_attr="_keyless_quotes",
            fetched_at_attr="_keyless_fetched_at",
            ttl_seconds=keyless_ttl_seconds,
            fetcher=keyless_fetcher,
            now=now,
        )
        merged = merge_market_snapshots(self._x402_enriched, self._keyless_quotes)
        if not merged:
            LOGGER.warning("Dual market snapshot merge produced no symbols")
        return copy.deepcopy(merged)

    def _maybe_refresh_layer(
        self,
        *,
        layer_name: str,
        snapshot_attr: str,
        fetched_at_attr: str,
        ttl_seconds: int,
        fetcher: Callable[[], dict[str, dict[str, Any]]],
        now: float,
    ) -> None:
        snapshot: dict[str, dict[str, Any]] = getattr(self, snapshot_attr)
        fetched_at: float = getattr(self, fetched_at_attr)
        age = now - fetched_at
        if ttl_seconds > 0 and snapshot and age < ttl_seconds:
            LOGGER.debug(
                "Reusing %s market snapshot (age=%.0fs ttl=%ss symbols=%s)",
                layer_name,
                age,
                ttl_seconds,
                len(snapshot),
            )
            return

        try:
            fresh = fetcher()
        except Exception as exc:
            LOGGER.warning("%s market snapshot fetch failed: %s", layer_name, exc)
            fresh = {}

        if fresh:
            setattr(self, snapshot_attr, copy.deepcopy(fresh))
            setattr(self, fetched_at_attr, now)
            LOGGER.info(
                "Refreshed %s market snapshot (ttl=%ss symbols=%s)",
                layer_name,
                ttl_seconds,
                len(fresh),
            )
            if layer_name == "x402":
                self._save_persisted()
        elif not snapshot:
            LOGGER.warning("%s market snapshot fetch returned empty and no cache exists", layer_name)
        else:
            LOGGER.warning(
                "%s market snapshot fetch returned empty; reusing stale cache (%s symbols)",
                layer_name,
                len(snapshot),
            )

    def reset(self) -> None:
        self._x402_enriched = {}
        self._x402_fetched_at = 0.0
        self._keyless_quotes = {}
        self._keyless_fetched_at = 0.0
        if self._persist_path is not None:
            try:
                self._persist_path.unlink(missing_ok=True)
            except OSError:
                pass

    # -- disk persistence (paid x402 layer only) ----------------------------

    def _load_persisted(self) -> None:
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            payload = json.loads(self._persist_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            LOGGER.warning("Could not load persisted x402 snapshot cache: %s", exc)
            return
        snapshot = payload.get("x402_enriched")
        fetched_at_epoch = payload.get("x402_fetched_at_epoch")
        if not isinstance(snapshot, dict) or not snapshot:
            return
        try:
            age = max(0.0, time.time() - float(fetched_at_epoch))
        except (TypeError, ValueError):
            return
        self._x402_enriched = snapshot
        # Translate persisted wall-clock age into this process's monotonic
        # clock so TTL math keeps working after a restart.
        self._x402_fetched_at = time.monotonic() - age
        LOGGER.info(
            "Restored persisted x402 snapshot (age=%.0fs symbols=%s); no paid refresh needed until TTL expires",
            age,
            len(snapshot),
        )

    def _save_persisted(self) -> None:
        if self._persist_path is None:
            return
        payload = {
            "x402_enriched": self._x402_enriched,
            "x402_fetched_at_epoch": time.time(),
        }
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._persist_path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(payload), encoding="utf-8")
            tmp_path.replace(self._persist_path)
        except OSError as exc:
            LOGGER.warning("Could not persist x402 snapshot cache: %s", exc)


_DEFAULT_CACHE = MarketSnapshotCache()
_DEFAULT_DUAL_CACHE = DualMarketSnapshotCache(persist_path=DEFAULT_PERSIST_PATH)


def get_market_snapshot_cache() -> MarketSnapshotCache:
    return _DEFAULT_CACHE


def get_dual_market_snapshot_cache() -> DualMarketSnapshotCache:
    return _DEFAULT_DUAL_CACHE
