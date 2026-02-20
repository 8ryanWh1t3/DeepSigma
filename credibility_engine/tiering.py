"""Credibility Engine — Hot/Warm/Cold Evidence Tiering.

Classifies evidence records into tiers based on age and TTL, provides
tier-aware queries for scoring (hot+warm) vs. audit (all), and runs
demotion sweeps to move aging evidence to warm/cold storage.

Compatible with the JSONL compaction tool's ``*-warm.jsonl`` /
``*-cold.jsonl`` naming convention.

Usage::

    from credibility_engine.tiering import EvidenceTierManager, TieringPolicy

    manager = EvidenceTierManager(store, TieringPolicy())
    summary = manager.sweep()
    scoring_claims = manager.get_scoring_claims()
"""
from __future__ import annotations

import enum
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from credibility_engine.store import CredibilityStore

logger = logging.getLogger(__name__)


# ── Enums & Config ───────────────────────────────────────────────────────────


class EvidenceTier(enum.Enum):
    """Evidence temperature tiers."""

    HOT = "hot"
    WARM = "warm"
    COLD = "cold"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, EvidenceTier):
            return NotImplemented
        order = {EvidenceTier.HOT: 0, EvidenceTier.WARM: 1, EvidenceTier.COLD: 2}
        return order[self] < order[other]


@dataclass
class TieringPolicy:
    """Configurable thresholds for evidence tier classification.

    Parameters
    ----------
    hot_max_age_minutes : int
        Maximum age (in minutes) for evidence to stay in the hot tier.
        Default: 1440 (24 hours).
    warm_max_age_minutes : int
        Maximum age for the warm tier. Beyond this → cold.
        Default: 43200 (30 days).
    ttl_expiry_demotes : bool
        If True, evidence with expired TTL (ttl_remaining <= 0) is
        demoted from hot to warm even if still within the age window.
    cold_excludes_scoring : bool
        If True, cold-tier evidence is excluded from CI scoring.
    """

    hot_max_age_minutes: int = 1440
    warm_max_age_minutes: int = 43200
    ttl_expiry_demotes: bool = True
    cold_excludes_scoring: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TieringSweepResult:
    """Result of a tiering sweep operation."""

    promoted: int = 0
    demoted: int = 0
    unchanged: int = 0
    by_tier: dict[str, int] = field(default_factory=lambda: {"hot": 0, "warm": 0, "cold": 0})
    files_processed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Tier Manager ─────────────────────────────────────────────────────────────


# Files that support tiering
_TIERABLE_FILES = [
    CredibilityStore.CLAIMS_FILE,
    CredibilityStore.DRIFT_FILE,
    CredibilityStore.SNAPSHOTS_FILE,
    CredibilityStore.CORRELATION_FILE,
    CredibilityStore.SYNC_FILE,
]

# Timestamp fields to check, in priority order
_TS_FIELDS = ("timestamp", "last_verified", "last_watermark")


def _parse_timestamp(record: dict[str, Any]) -> datetime | None:
    """Extract and parse the best available timestamp from a record."""
    for field_name in _TS_FIELDS:
        ts = record.get(field_name, "")
        if not ts:
            continue
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
    return None


class EvidenceTierManager:
    """Manages hot/warm/cold evidence tiering for a CredibilityStore.

    Parameters
    ----------
    store : CredibilityStore
        The persistence store to tier.
    policy : TieringPolicy
        Classification thresholds.
    """

    def __init__(
        self,
        store: CredibilityStore,
        policy: TieringPolicy | None = None,
    ) -> None:
        self.store = store
        self.policy = policy or TieringPolicy()

    # ── Classification ────────────────────────────────────────────

    def classify(
        self,
        record: dict[str, Any],
        now: datetime | None = None,
    ) -> EvidenceTier:
        """Classify a single record into a tier.

        Classification rules:
        1. If age < hot_max_age_minutes AND TTL not expired → HOT
        2. If age < hot_max_age_minutes BUT TTL expired AND ttl_expiry_demotes → WARM
        3. If age < warm_max_age_minutes → WARM
        4. Otherwise → COLD
        5. If no timestamp is found → HOT (safe default)
        """
        if now is None:
            now = datetime.now(timezone.utc)

        ts = _parse_timestamp(record)
        if ts is None:
            return EvidenceTier.HOT

        # Ensure timezone-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        age_minutes = (now - ts).total_seconds() / 60

        if age_minutes <= self.policy.hot_max_age_minutes:
            # Check TTL expiry demotion
            ttl = record.get("ttl_remaining")
            if (
                ttl is not None
                and ttl <= 0
                and self.policy.ttl_expiry_demotes
            ):
                return EvidenceTier.WARM
            return EvidenceTier.HOT

        if age_minutes <= self.policy.warm_max_age_minutes:
            return EvidenceTier.WARM

        return EvidenceTier.COLD

    # ── Sweep ─────────────────────────────────────────────────────

    def sweep(self, now: datetime | None = None) -> TieringSweepResult:
        """Run a demotion sweep across all tierable files.

        Reads each file, reclassifies records, and writes them to the
        appropriate tier file (primary, warm, cold).

        Returns a summary of the sweep.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        result = TieringSweepResult()

        for filename in _TIERABLE_FILES:
            # Load all records across tiers
            all_records = self._load_all_tiers(filename)
            if not all_records:
                continue

            result.files_processed += 1
            hot: list[dict[str, Any]] = []
            warm: list[dict[str, Any]] = []
            cold: list[dict[str, Any]] = []

            for record in all_records:
                prev_tier = record.get("_tier")
                tier = self.classify(record, now)

                # Track promotion/demotion
                if prev_tier is not None:
                    if _tier_order(tier.value) < _tier_order(prev_tier):
                        result.promoted += 1
                    elif _tier_order(tier.value) > _tier_order(prev_tier):
                        result.demoted += 1
                    else:
                        result.unchanged += 1
                else:
                    result.unchanged += 1

                # Tag the record (non-destructive metadata)
                record["_tier"] = tier.value

                if tier == EvidenceTier.HOT:
                    hot.append(record)
                elif tier == EvidenceTier.WARM:
                    warm.append(record)
                else:
                    cold.append(record)

            result.by_tier["hot"] += len(hot)
            result.by_tier["warm"] += len(warm)
            result.by_tier["cold"] += len(cold)

            # Write tier files
            self.store.write_batch(filename, hot)
            self.store.write_warm(filename, warm)
            self.store.write_cold(filename, cold)

        return result

    # ── Tier-aware queries ────────────────────────────────────────

    def get_claims(self, tier_filter: EvidenceTier | None = None) -> list[dict[str, Any]]:
        """Load claims filtered by tier.

        - HOT: primary file only
        - WARM: primary + warm
        - None/ALL: primary + warm + cold
        """
        filename = CredibilityStore.CLAIMS_FILE
        if tier_filter == EvidenceTier.HOT:
            return self.store.load_all(filename)
        if tier_filter == EvidenceTier.WARM:
            return self.store.load_all(filename) + self.store.load_warm(filename)
        return self._load_all_tiers(filename)

    def get_drift_events(
        self,
        tier_filter: EvidenceTier | None = None,
        n: int = 500,
    ) -> list[dict[str, Any]]:
        """Load drift events filtered by tier, capped at n records."""
        filename = CredibilityStore.DRIFT_FILE
        if tier_filter == EvidenceTier.HOT:
            records = self.store.load_all(filename)
        elif tier_filter == EvidenceTier.WARM:
            records = self.store.load_all(filename) + self.store.load_warm(filename)
        else:
            records = self._load_all_tiers(filename)
        return records[-n:]

    def get_scoring_claims(self) -> list[dict[str, Any]]:
        """Get claims for CI scoring: hot + warm tiers only."""
        return self.get_claims(EvidenceTier.WARM)

    def get_scoring_drift(self, n: int = 500) -> list[dict[str, Any]]:
        """Get drift events for CI scoring: hot + warm, capped."""
        return self.get_drift_events(EvidenceTier.WARM, n=n)

    def tier_summary(self) -> dict[str, Any]:
        """Return counts by tier for each data type."""
        summary: dict[str, dict[str, int]] = {}

        for filename in _TIERABLE_FILES:
            stem = filename.replace(".jsonl", "")
            hot_count = len(self.store.load_all(filename))
            warm_count = len(self.store.load_warm(filename))
            cold_count = len(self.store.load_cold(filename))
            summary[stem] = {
                "hot": hot_count,
                "warm": warm_count,
                "cold": cold_count,
                "total": hot_count + warm_count + cold_count,
            }

        return {
            "policy": self.policy.to_dict(),
            "tiers": summary,
        }

    # ── Internal ──────────────────────────────────────────────────

    def _load_all_tiers(self, filename: str) -> list[dict[str, Any]]:
        """Load records from all three tier files for a given filename."""
        hot = self.store.load_all(filename)
        warm = self.store.load_warm(filename)
        cold = self.store.load_cold(filename)
        return hot + warm + cold


def _tier_order(tier_value: str) -> int:
    """Return numeric order for tier comparison."""
    return {"hot": 0, "warm": 1, "cold": 2}.get(tier_value, 1)
