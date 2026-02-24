"""Credibility Engine Simulation - Tick-based Engine.

Maintains simulation state and advances it each tick based on
scenario phase parameters.  Produces JSON-compatible snapshots
for all 7 dashboard data files.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from models import (
    Claim,
    CorrelationCluster,
    DriftFingerprint,
    SyncRegion,
    make_baseline_claims,
    make_baseline_clusters,
    make_baseline_fingerprints,
    make_baseline_sync,
)
from scenarios import SCENARIOS

# Each tick advances sim time by 15 minutes.
SIM_STEP = timedelta(minutes=15)


class CredibilityEngine:
    """Tick-based credibility engine simulation."""

    def __init__(self, scenario_name: str = "day0") -> None:
        self.scenario_name = scenario_name
        self.scenario = SCENARIOS[scenario_name]
        self.tick_num = 0
        self.sim_time = datetime.now(timezone.utc)

        # State
        self.claims: list[Claim] = make_baseline_claims()
        self.clusters: list[CorrelationCluster] = make_baseline_clusters()
        self.sync_regions: list[SyncRegion] = make_baseline_sync()
        self.fingerprints: list[DriftFingerprint] = make_baseline_fingerprints()

        # Index components
        self.integrity = 42
        self.drift_penalty = 0
        self.correlation_penalty = 0
        self.quorum_penalty = 0
        self.ttl_penalty = 0
        self.confirmation_bonus = 5

        # Drift accumulation
        self.drift_total = 0
        self.drift_by_severity = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        self.drift_by_category = {
            "timing_entropy": 0, "correlation_drift": 0,
            "confidence_volatility": 0, "ttl_compression": 0,
            "external_mismatch": 0,
        }
        self.drift_by_region = {"East": 0, "Central": 0, "West": 0}
        self.drift_auto_resolved = 0
        self.drift_pending = 0
        self.drift_escalated = 0
        self.drift_hourly: list[int] = [0] * 24

        # Trend history (last 5 index values)
        self.trend_history: list[int] = []

        # Seal chain tracking
        self.seal_chain_length = 157
        self.patches_applied = 0
        self.seals_created = 0
        self.nodes_added = 0
        self.edges_added = 0
        self.nodes_modified = 0

    # -- Phase resolution ------------------------------------------------------

    def _current_phase(self) -> dict:
        """Find the active phase for the current tick."""
        for phase in self.scenario["phases"]:
            if phase["start"] <= self.tick_num <= phase["end"]:
                return phase
        return self.scenario["phases"][-1]

    # -- Tick -------------------------------------------------------------------

    def tick(self) -> None:
        """Advance the simulation by one tick."""
        phase = self._current_phase()
        self.tick_num += 1
        self.sim_time += SIM_STEP

        self._decay_ttl(phase)
        self._inject_drift(phase)
        self._adjust_correlations(phase)
        self._apply_claim_effects(phase)
        self._update_sync(phase)
        self._recalculate_index(phase)
        self._update_trend()
        self._track_operations(phase)

    # -- Subsystem updates -----------------------------------------------------

    def _decay_ttl(self, phase: dict) -> None:
        """Decrement TTL remaining on all claims."""
        decay = int(15 * phase.get("ttl_decay_multiplier", 1.0))
        for claim in self.claims:
            claim.ttl_remaining_minutes = max(0, claim.ttl_remaining_minutes - decay)
            # Refresh TTL if still verified and TTL gets low
            if (claim.status == "VERIFIED"
                    and claim.ttl_remaining_minutes < 30
                    and claim.claim_id not in phase.get("claim_effects", {})):
                claim.ttl_remaining_minutes = claim.ttl_minutes
                claim.last_verified = self.sim_time.isoformat().replace("+00:00", "Z")

    def _inject_drift(self, phase: dict) -> None:
        """Add drift events for this tick."""
        rate = phase["drift_rate"]
        count = max(0, rate + random.randint(-2, 2))

        sev_weights = phase["severity_weights"]
        cat_weights = phase["category_weights"]
        sevs = ["low", "medium", "high", "critical"]
        cats = list(self.drift_by_category.keys())
        regions = ["East", "Central", "West"]

        auto_resolve_rate = 0.92 if phase.get("patch_active", True) else 0.40

        for _ in range(count):
            sev = random.choices(sevs, weights=sev_weights, k=1)[0]
            cat = random.choices(cats, weights=cat_weights, k=1)[0]
            reg = random.choice(regions)

            self.drift_total += 1
            self.drift_by_severity[sev] += 1
            self.drift_by_category[cat] += 1
            self.drift_by_region[reg] += 1

            if random.random() < auto_resolve_rate:
                self.drift_auto_resolved += 1
            elif random.random() < 0.7:
                self.drift_pending += 1
            else:
                self.drift_escalated += 1

        # Update hourly distribution (slot = sim hour mod 24)
        hour_slot = int((self.sim_time.hour + self.sim_time.minute / 60)) % 24
        self.drift_hourly[hour_slot] += count

        # Update fingerprint recurrence
        fp_escalation = phase.get("fingerprint_escalation", {})
        for fp in self.fingerprints:
            if random.random() < 0.3:
                fp.recurrence_count += random.randint(0, 2)
            if fp.fingerprint in fp_escalation:
                esc = fp_escalation[fp.fingerprint]
                fp.severity = esc["severity"]
                fp.auto_resolved = esc["auto_resolved"]

    def _adjust_correlations(self, phase: dict) -> None:
        """Move correlation coefficients toward scenario targets."""
        targets = phase["correlation_targets"]
        speed = phase.get("correlation_drift_speed", 0.01)

        for cluster in self.clusters:
            target = targets.get(cluster.cluster_id, cluster.coefficient)
            diff = target - cluster.coefficient
            if abs(diff) < 0.005:
                cluster.coefficient = target
            else:
                jitter = random.uniform(-0.005, 0.005)
                cluster.coefficient += diff * speed / max(abs(diff), speed) + jitter
                cluster.coefficient = max(0.0, min(1.0, cluster.coefficient))

    def _apply_claim_effects(self, phase: dict) -> None:
        """Apply scenario-driven claim state changes."""
        effects = phase.get("claim_effects", {})
        for claim in self.claims:
            if claim.claim_id in effects:
                eff = effects[claim.claim_id]
                # Status
                claim.status = eff.get("status", claim.status)
                # Confidence
                if "confidence_target" in eff:
                    target = eff["confidence_target"]
                    if target is None:
                        claim.confidence = None
                    elif claim.confidence is not None:
                        diff = target - claim.confidence
                        claim.confidence += diff * 0.15
                        claim.confidence = round(claim.confidence, 2)
                    else:
                        claim.confidence = target
                # Margin
                if "margin_target" in eff:
                    target = eff["margin_target"]
                    if claim.margin > target:
                        claim.margin = max(target, claim.margin - 1)
                    elif claim.margin < target:
                        claim.margin = min(target, claim.margin + 1)
                # Correlation groups
                if "correlation_groups_actual" in eff:
                    claim.correlation_groups_actual = eff["correlation_groups_actual"]
                # Out of band
                if "out_of_band_present" in eff:
                    claim.out_of_band_present = eff["out_of_band_present"]
                # Degradation reason
                if "degradation_reason" in eff:
                    claim.degradation_reason = eff["degradation_reason"]
                # Update last_verified for active claims
                if claim.status == "VERIFIED":
                    claim.last_verified = (
                        self.sim_time.isoformat().replace("+00:00", "Z")
                    )
            else:
                # Claims not under pressure stay healthy
                if claim.status == "DEGRADED" and claim.claim_id not in effects:
                    pass  # Keep current state unless scenario says otherwise

        # Auto-evaluate quorum: if margin <= 0 and status isn't already UNKNOWN
        for claim in self.claims:
            if claim.margin <= 0 and claim.status != "UNKNOWN":
                if claim.claim_id in effects and effects[claim.claim_id].get("status") == "UNKNOWN":
                    claim.status = "UNKNOWN"
                    claim.confidence = None
            # TTL expiry forces UNKNOWN
            if claim.ttl_remaining_minutes <= 0 and claim.status == "VERIFIED":
                if claim.claim_id not in effects:
                    claim.ttl_remaining_minutes = claim.ttl_minutes
                    claim.last_verified = (
                        self.sim_time.isoformat().replace("+00:00", "Z")
                    )

    def _update_sync(self, phase: dict) -> None:
        """Move sync plane metrics toward scenario targets."""
        targets = phase.get("sync_targets", {})
        speed = phase.get("sync_drift_speed", 1.0)

        for sr in self.sync_regions:
            if sr.region not in targets:
                continue
            t = targets[sr.region]

            # Time skew
            diff = t["skew"] - sr.time_skew_ms
            sr.time_skew_ms += int(diff * min(speed * 0.1, 1.0))
            sr.time_skew_ms = max(0, sr.time_skew_ms + random.randint(-2, 2))

            # Watermark lag
            diff_lag = t["lag"] - sr.watermark_lag_s
            sr.watermark_lag_s += diff_lag * min(speed * 0.1, 1.0)
            sr.watermark_lag_s = max(0.1, sr.watermark_lag_s + random.uniform(-0.1, 0.1))

            # Replay flags
            target_replays = t["replays"]
            if sr.replay_flags_count < target_replays:
                if random.random() < 0.3:
                    sr.replay_flags_count += 1
            elif sr.replay_flags_count > target_replays:
                if random.random() < 0.2:
                    sr.replay_flags_count = max(0, sr.replay_flags_count - 1)

            # Nodes down
            target_down = t.get("nodes_down", 0)
            sr.sync_nodes_healthy = sr.sync_nodes - target_down

            # Watermark advancing if lag < critical
            sr.watermark_advancing = sr.watermark_lag_s < 30

            # Update timestamp
            sr.last_watermark = self.sim_time.isoformat().replace("+00:00", "Z")

            # Warning detail
            if sr.status == "WARN":
                issues = []
                if sr.time_skew_ms > 100:
                    issues.append(f"time skew {sr.time_skew_ms}ms")
                if sr.replay_flags_count > 0:
                    issues.append(
                        f"{sr.replay_flags_count} replay flag(s)")
                if sr.sync_nodes_healthy < sr.sync_nodes:
                    issues.append(
                        f"{sr.sync_nodes - sr.sync_nodes_healthy} sync node(s) degraded")
                sr.warning_detail = " — ".join(issues) if issues else None
            elif sr.status == "CRITICAL":
                issues = []
                if sr.time_skew_ms > 500:
                    issues.append(f"CRITICAL time skew {sr.time_skew_ms}ms")
                if sr.replay_flags_count >= 5:
                    issues.append(
                        f"{sr.replay_flags_count} replay flags — backfill suspected")
                if sr.watermark_lag_s > 30:
                    issues.append(f"watermark stalled ({sr.watermark_lag_s:.1f}s lag)")
                sr.warning_detail = " — ".join(issues) if issues else None
            else:
                sr.warning_detail = None

    def _recalculate_index(self, phase: dict) -> None:
        """Recalculate all Credibility Index components.

        Uses rate-based drift penalty (current phase severity, not
        accumulated totals) to prevent runaway penalty growth.
        """
        # Integrity — moves toward phase target
        target_int = phase.get("integrity_target", 37)
        diff = target_int - self.integrity
        self.integrity += int(diff * 0.15) + (1 if diff > 0 else -1 if diff < 0 else 0)
        self.integrity = max(0, min(50, self.integrity))

        # Drift penalty — rate-based (current phase severity profile)
        rate = phase["drift_rate"]
        sev = phase["severity_weights"]
        self.drift_penalty = -int(
            rate * (sev[3] * 6 + sev[2] * 2 + sev[1] * 0.3)
        )
        self.drift_penalty = max(-15, self.drift_penalty)

        # Correlation penalty — based on current cluster coefficients
        max_coeff = max(c.coefficient for c in self.clusters)
        review_count = sum(1 for c in self.clusters if c.coefficient > 0.7)
        critical_count_corr = sum(1 for c in self.clusters if c.coefficient > 0.9)
        self.correlation_penalty = -(
            critical_count_corr * 3 + review_count * 1
            + int(max(0, max_coeff - 0.6) * 5)
        )
        self.correlation_penalty = max(-12, self.correlation_penalty)

        # Quorum penalty — based on current claim margins
        unknown_count = sum(1 for c in self.claims if c.status == "UNKNOWN")
        margin_1_count = sum(
            1 for c in self.claims
            if c.margin == 1 and c.status != "UNKNOWN"
        )
        self.quorum_penalty = -(unknown_count * 2 + margin_1_count * 1)
        self.quorum_penalty = max(-10, self.quorum_penalty)

        # TTL penalty — based on expired or near-expired claims
        expired_count = sum(
            1 for c in self.claims if c.ttl_remaining_minutes <= 0
        )
        near_expired = sum(
            1 for c in self.claims if 0 < c.ttl_remaining_minutes <= 30
        )
        self.ttl_penalty = -(expired_count * 2 + near_expired * 1)
        self.ttl_penalty = max(-6, self.ttl_penalty)

        # Confirmation bonus
        self.confirmation_bonus = phase.get("confirmation_bonus", 3)

    def _update_trend(self) -> None:
        """Track rolling index history."""
        score = self.credibility_index
        self.trend_history.append(score)
        if len(self.trend_history) > 5:
            self.trend_history = self.trend_history[-5:]

    def _track_operations(self, phase: dict) -> None:
        """Track operational metrics for packet generation."""
        if phase.get("patch_active", True):
            new_patches = random.randint(1, 4)
            self.patches_applied += new_patches
            self.seals_created += random.randint(0, new_patches)
        self.nodes_added += random.randint(1, 5)
        self.edges_added += random.randint(2, 8)
        self.nodes_modified += random.randint(0, 3)
        self.seal_chain_length += 1

    # -- Computed properties ---------------------------------------------------

    @property
    def credibility_index(self) -> int:
        base = 60
        score = (
            base + self.integrity + self.drift_penalty
            + self.correlation_penalty + self.quorum_penalty
            + self.ttl_penalty + self.confirmation_bonus
        )
        return max(0, min(100, score))

    @property
    def index_band(self) -> str:
        s = self.credibility_index
        if s >= 95:
            return "Stable"
        if s >= 85:
            return "Minor Drift"
        if s >= 70:
            return "Elevated Risk"
        if s >= 50:
            return "Structural Degradation"
        return "Compromised"

    @property
    def index_band_color(self) -> str:
        s = self.credibility_index
        if s >= 95:
            return "green"
        if s >= 85:
            return "yellow"
        return "red"

    @property
    def auto_patch_rate(self) -> float:
        if self.drift_total == 0:
            return 1.0
        return round(self.drift_auto_resolved / max(self.drift_total, 1), 2)

    @property
    def active_drift_signals(self) -> int:
        return sum(
            1 for fp in self.fingerprints if not fp.auto_resolved
        )

    # -- Scenario switching ----------------------------------------------------

    def set_scenario(self, scenario_name: str) -> None:
        """Switch to a different scenario without resetting state."""
        if scenario_name in SCENARIOS:
            self.scenario_name = scenario_name
            self.scenario = SCENARIOS[scenario_name]
            self.tick_num = 0

    # -- JSON snapshot export --------------------------------------------------

    def snapshot_credibility(self) -> dict:
        """Produce credibility_snapshot.json."""
        labels = ["T-4", "T-3", "T-2", "T-1", "Now"]
        history = self.trend_history[-5:]
        while len(history) < 5:
            history.insert(0, history[0] if history else self.credibility_index)

        return {
            "index_score": self.credibility_index,
            "index_band": self.index_band,
            "index_band_color": self.index_band_color,
            "trend_points": list(history),
            "trend_labels": labels,
            "last_updated": self.sim_time.isoformat().replace("+00:00", "Z"),
            "total_nodes": 36000,
            "regions": 3,
            "active_drift_signals": self.active_drift_signals,
            "auto_patch_rate": self.auto_patch_rate,
            "bands": [
                {"range": "95\u2013100", "label": "Stable", "action": "Monitor"},
                {"range": "85\u201394", "label": "Minor Drift",
                 "action": "Review flagged claims"},
                {"range": "70\u201384", "label": "Elevated Risk",
                 "action": "Patch required"},
                {"range": "50\u201369", "label": "Structural Degradation",
                 "action": "Immediate remediation"},
                {"range": "<50", "label": "Compromised",
                 "action": "Halt dependent decisions"},
            ],
            "components": {
                "tier_weighted_integrity": self.integrity,
                "drift_penalty": self.drift_penalty,
                "correlation_risk": self.correlation_penalty,
                "quorum_margin": self.quorum_penalty,
                "ttl_expiration": self.ttl_penalty,
                "confirmation_bonus": self.confirmation_bonus,
                "base": 60,
            },
        }

    def snapshot_claims(self) -> dict:
        """Produce claims_tier0.json."""
        return {
            "tier": 0,
            "total_count": 200,
            "claims": [c.to_dict() for c in self.claims],
        }

    def snapshot_drift(self) -> dict:
        """Produce drift_events_24h.json."""
        window_end = self.sim_time
        window_start = window_end - timedelta(hours=24)

        # Derive top fingerprints sorted by recurrence
        sorted_fps = sorted(
            self.fingerprints,
            key=lambda f: f.recurrence_count,
            reverse=True,
        )

        return {
            "window": "24h",
            "window_start": window_start.isoformat().replace("+00:00", "Z"),
            "window_end": window_end.isoformat().replace("+00:00", "Z"),
            "total_count": self.drift_total,
            "by_severity": dict(self.drift_by_severity),
            "by_category": dict(self.drift_by_category),
            "by_region": dict(self.drift_by_region),
            "auto_resolved": self.drift_auto_resolved,
            "pending_review": self.drift_pending,
            "escalated": self.drift_escalated,
            "top_fingerprints": [fp.to_dict() for fp in sorted_fps[:5]],
            "hourly_distribution": list(self.drift_hourly),
        }

    def snapshot_correlation(self) -> dict:
        """Produce correlation_map.json."""
        return {
            "clusters": [c.to_dict() for c in self.clusters],
            "thresholds": {
                "ok_max": 0.7,
                "review_max": 0.9,
                "critical_min": 0.9,
            },
        }

    def snapshot_ttl(self) -> dict:
        """Produce ttl_timeline.json."""
        # Generate TTL buckets based on current state
        base_expiring = max(100, 342 + self.tick_num * 3)
        phase = self._current_phase()
        multiplier = phase.get("ttl_decay_multiplier", 1.0)

        buckets = []
        bucket_defs = [
            ("0\u201330min", 0.13),
            ("30\u201360min", 0.21),
            ("1\u20132h", 0.35),
            ("2\u20134h", 0.31),
        ]
        total_expiring = 0
        for label, frac in bucket_defs:
            count = int(base_expiring * frac * min(multiplier, 3.0))
            count = max(1, count + random.randint(-3, 3))
            total_expiring += count

            # Distribute by tier
            t0 = max(0, int(count * 0.04) + random.randint(0, 2))
            t1 = int(count * 0.35)
            t2 = int(count * 0.38)
            t3 = count - t0 - t1 - t2

            # Distribute by region
            east = int(count * 0.32)
            central = int(count * 0.38)
            west = count - east - central

            buckets.append({
                "bucket": label,
                "count": count,
                "by_tier": {"0": t0, "1": t1, "2": t2, "3": t3},
                "by_region": {"East": east, "Central": central, "West": west},
            })

        # Tier 0 expirations from actual claim state
        tier0_exp = []
        for claim in self.claims:
            if claim.ttl_remaining_minutes <= 60:
                tier0_exp.append({
                    "evidence_id": f"EV-{claim.domain}-{random.randint(100, 9999):04d}",
                    "claim_id": claim.claim_id,
                    "ttl_remaining_minutes": max(0, claim.ttl_remaining_minutes),
                    "source": f"S-{claim.domain}-{random.randint(1, 20):03d}",
                    "region": claim.region,
                })

        clustering = multiplier > 1.5 or len(tier0_exp) > 1
        clustering_desc = ""
        if clustering:
            clustering_desc = (
                f"{random.randint(40, 120)} Tier 1 evidence nodes expire "
                f"within a 15-minute window at T+{random.randint(1, 3)}h"
                f"{random.randint(0, 59):02d}m"
            )

        return {
            "window": "next_4h",
            "total_evidence_nodes": 9500,
            "expiring_within_window": total_expiring,
            "clustering_warning": clustering,
            "clustering_description": clustering_desc,
            "upcoming_expirations": buckets,
            "tier_0_expirations": tier0_exp,
        }

    def snapshot_sync(self) -> dict:
        """Produce sync_integrity.json."""
        # Compute federation skew
        max_skew = max(sr.time_skew_ms for sr in self.sync_regions)
        min_skew = min(sr.time_skew_ms for sr in self.sync_regions)
        cross_skew = max_skew - min_skew + random.randint(0, 10)

        fed_status = "OK" if cross_skew < 200 else "WARN"
        if cross_skew > 500:
            fed_status = "CRITICAL"

        return {
            "regions": [sr.to_dict() for sr in self.sync_regions],
            "federation": {
                "cross_region_skew_ms": cross_skew,
                "max_acceptable_skew_ms": 200,
                "status": fed_status,
            },
            "thresholds": {
                "time_skew_warn_ms": 100,
                "time_skew_critical_ms": 500,
                "watermark_lag_warn_s": 5,
                "watermark_lag_critical_s": 30,
                "replay_warn_count": 1,
                "replay_critical_count": 5,
            },
        }

    def all_snapshots(self) -> dict[str, dict]:
        """Return all 7 JSON snapshots keyed by filename (no extension)."""
        return {
            "credibility_snapshot": self.snapshot_credibility(),
            "claims_tier0": self.snapshot_claims(),
            "drift_events_24h": self.snapshot_drift(),
            "correlation_map": self.snapshot_correlation(),
            "ttl_timeline": self.snapshot_ttl(),
            "sync_integrity": self.snapshot_sync(),
        }
