"""Credibility Engine Simulation - Scenario Definitions.

Four scenarios that progress from baseline stability through
institutional entropy, coordinated darkness, and external mismatch.

Each scenario is a list of phases. Each phase specifies:
- tick range (start, end)
- drift injection rate and severity distribution
- correlation coefficient targets per cluster
- claim pressure (margin compression, TTL decay multipliers)
- sync plane degradation parameters
- index component adjustments

Abstract institutional credibility architecture.
No real-world system modeled.
"""

# Severity distribution weights: (low, medium, high, critical)
# Category distribution weights: (timing_entropy, correlation_drift,
#   confidence_volatility, ttl_compression, external_mismatch)

SCENARIOS = {
    "day0": {
        "description": "Baseline — stable lattice, healthy quorum, minimal drift",
        "phases": [
            {
                "start": 0, "end": 999,
                "drift_rate": 3,
                "severity_weights": (0.70, 0.22, 0.07, 0.01),
                "category_weights": (0.30, 0.15, 0.25, 0.20, 0.10),
                "correlation_targets": {
                    "CG-001": 0.42, "CG-002": 0.55, "CG-003": 0.48,
                    "CG-004": 0.34, "CG-005": 0.45, "CG-006": 0.38,
                },
                "correlation_drift_speed": 0.01,
                "claim_effects": {},
                "sync_targets": {
                    "East":    {"skew": 12, "lag": 0.8, "replays": 0, "nodes_down": 0},
                    "Central": {"skew": 18, "lag": 1.2, "replays": 0, "nodes_down": 0},
                    "West":    {"skew": 8,  "lag": 0.5, "replays": 0, "nodes_down": 0},
                },
                "sync_drift_speed": 0.5,
                "integrity_target": 32,
                "confirmation_bonus": 5,
                "ttl_decay_multiplier": 1.0,
                "patch_active": True,
                "fingerprint_escalation": {},
            },
        ],
    },

    "day1": {
        "description": "Entropy emerges — drift increases, correlation crosses REVIEW, quorum compresses",
        "phases": [
            # Phase 1: Stable opening (ticks 0-20)
            {
                "start": 0, "end": 20,
                "drift_rate": 3,
                "severity_weights": (0.70, 0.22, 0.07, 0.01),
                "category_weights": (0.30, 0.15, 0.25, 0.20, 0.10),
                "correlation_targets": {
                    "CG-001": 0.42, "CG-002": 0.58, "CG-003": 0.50,
                    "CG-004": 0.34, "CG-005": 0.45, "CG-006": 0.38,
                },
                "correlation_drift_speed": 0.01,
                "claim_effects": {},
                "sync_targets": {
                    "East":    {"skew": 12, "lag": 0.8, "replays": 0, "nodes_down": 0},
                    "Central": {"skew": 20, "lag": 1.5, "replays": 0, "nodes_down": 0},
                    "West":    {"skew": 10, "lag": 0.6, "replays": 0, "nodes_down": 0},
                },
                "sync_drift_speed": 0.5,
                "integrity_target": 32,
                "confirmation_bonus": 5,
                "ttl_decay_multiplier": 1.0,
                "patch_active": True,
                "fingerprint_escalation": {},
            },
            # Phase 2: Drift accelerates, correlation rises (ticks 21-50)
            {
                "start": 21, "end": 50,
                "drift_rate": 6,
                "severity_weights": (0.55, 0.30, 0.12, 0.03),
                "category_weights": (0.35, 0.20, 0.20, 0.15, 0.10),
                "correlation_targets": {
                    "CG-001": 0.48, "CG-002": 0.74, "CG-003": 0.58,
                    "CG-004": 0.36, "CG-005": 0.50, "CG-006": 0.40,
                },
                "correlation_drift_speed": 0.02,
                "claim_effects": {},
                "sync_targets": {
                    "East":    {"skew": 18, "lag": 1.2, "replays": 0, "nodes_down": 0},
                    "Central": {"skew": 35, "lag": 2.0, "replays": 0, "nodes_down": 0},
                    "West":    {"skew": 14, "lag": 0.8, "replays": 0, "nodes_down": 0},
                },
                "sync_drift_speed": 1.0,
                "integrity_target": 32,
                "confirmation_bonus": 4,
                "ttl_decay_multiplier": 1.5,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                },
            },
            # Phase 3: Quorum compression (ticks 51-70)
            {
                "start": 51, "end": 70,
                "drift_rate": 8,
                "severity_weights": (0.45, 0.35, 0.15, 0.05),
                "category_weights": (0.30, 0.25, 0.20, 0.15, 0.10),
                "correlation_targets": {
                    "CG-001": 0.52, "CG-002": 0.78, "CG-003": 0.62,
                    "CG-004": 0.38, "CG-005": 0.52, "CG-006": 0.42,
                },
                "correlation_drift_speed": 0.02,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.78,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Evidence-C2-014 confidence dropped below 0.80 threshold",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 22, "lag": 1.5, "replays": 0, "nodes_down": 0},
                    "Central": {"skew": 45, "lag": 2.3, "replays": 1, "nodes_down": 1},
                    "West":    {"skew": 16, "lag": 1.0, "replays": 0, "nodes_down": 0},
                },
                "sync_drift_speed": 1.5,
                "integrity_target": 32,
                "confirmation_bonus": 3,
                "ttl_decay_multiplier": 2.0,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                },
            },
            # Phase 4: Holds at Minor Drift (ticks 71+)
            {
                "start": 71, "end": 999,
                "drift_rate": 7,
                "severity_weights": (0.50, 0.30, 0.15, 0.05),
                "category_weights": (0.30, 0.22, 0.22, 0.16, 0.10),
                "correlation_targets": {
                    "CG-001": 0.54, "CG-002": 0.78, "CG-003": 0.64,
                    "CG-004": 0.38, "CG-005": 0.54, "CG-006": 0.42,
                },
                "correlation_drift_speed": 0.01,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.78,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Evidence-C2-014 confidence dropped below 0.80 threshold",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 22, "lag": 1.5, "replays": 0, "nodes_down": 0},
                    "Central": {"skew": 45, "lag": 2.3, "replays": 1, "nodes_down": 1},
                    "West":    {"skew": 16, "lag": 1.0, "replays": 0, "nodes_down": 0},
                },
                "sync_drift_speed": 0.5,
                "integrity_target": 31,
                "confirmation_bonus": 3,
                "ttl_decay_multiplier": 1.5,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                },
            },
        ],
    },

    "day2": {
        "description": "Coordinated darkness — silent nodes, UNKNOWN claim, sync degradation",
        "phases": [
            # Phase 1: Starting from Day1 end state (ticks 0-10)
            {
                "start": 0, "end": 10,
                "drift_rate": 7,
                "severity_weights": (0.50, 0.30, 0.15, 0.05),
                "category_weights": (0.30, 0.22, 0.22, 0.16, 0.10),
                "correlation_targets": {
                    "CG-001": 0.54, "CG-002": 0.78, "CG-003": 0.64,
                    "CG-004": 0.38, "CG-005": 0.54, "CG-006": 0.42,
                },
                "correlation_drift_speed": 0.02,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.78,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Evidence-C2-014 confidence dropped below 0.80 threshold",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 22, "lag": 1.5, "replays": 0, "nodes_down": 0},
                    "Central": {"skew": 50, "lag": 2.5, "replays": 1, "nodes_down": 1},
                    "West":    {"skew": 16, "lag": 1.0, "replays": 0, "nodes_down": 0},
                },
                "sync_drift_speed": 1.0,
                "integrity_target": 31,
                "confirmation_bonus": 3,
                "ttl_decay_multiplier": 1.5,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                },
            },
            # Phase 2: Silent nodes increase, correlation climbs (ticks 11-30)
            {
                "start": 11, "end": 30,
                "drift_rate": 10,
                "severity_weights": (0.40, 0.30, 0.22, 0.08),
                "category_weights": (0.25, 0.28, 0.18, 0.14, 0.15),
                "correlation_targets": {
                    "CG-001": 0.58, "CG-002": 0.82, "CG-003": 0.76,
                    "CG-004": 0.42, "CG-005": 0.60, "CG-006": 0.45,
                },
                "correlation_drift_speed": 0.03,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.72,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Evidence-C2-014 confidence dropped below 0.80 threshold",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 35, "lag": 2.0, "replays": 0, "nodes_down": 0},
                    "Central": {"skew": 80, "lag": 4.5, "replays": 2, "nodes_down": 1},
                    "West":    {"skew": 28, "lag": 1.8, "replays": 0, "nodes_down": 0},
                },
                "sync_drift_speed": 2.0,
                "integrity_target": 31,
                "confirmation_bonus": 2,
                "ttl_decay_multiplier": 2.5,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "high", "auto_resolved": False},
                },
            },
            # Phase 3: Tier0 flips to UNKNOWN (ticks 31-50)
            {
                "start": 31, "end": 50,
                "drift_rate": 12,
                "severity_weights": (0.35, 0.30, 0.25, 0.10),
                "category_weights": (0.22, 0.30, 0.18, 0.15, 0.15),
                "correlation_targets": {
                    "CG-001": 0.60, "CG-002": 0.85, "CG-003": 0.82,
                    "CG-004": 0.44, "CG-005": 0.62, "CG-006": 0.48,
                },
                "correlation_drift_speed": 0.03,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.68,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Evidence-C2-014 confidence dropped below 0.80 threshold",
                    },
                    "CLM-T0-003": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — Source-W2-007 offline, "
                            "TTL expired on 2 evidence nodes",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 45, "lag": 3.0, "replays": 0, "nodes_down": 0},
                    "Central": {"skew": 120, "lag": 8.0, "replays": 3, "nodes_down": 1},
                    "West":    {"skew": 40, "lag": 2.5, "replays": 1, "nodes_down": 0},
                },
                "sync_drift_speed": 3.0,
                "integrity_target": 29,
                "confirmation_bonus": 1,
                "ttl_decay_multiplier": 3.0,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "high", "auto_resolved": False},
                    "TTL-BATCH-EXPIRE-T1": {"severity": "medium", "auto_resolved": False},
                },
            },
            # Phase 4: Sync watermark lag peaks (ticks 51-70)
            {
                "start": 51, "end": 70,
                "drift_rate": 14,
                "severity_weights": (0.30, 0.30, 0.28, 0.12),
                "category_weights": (0.20, 0.28, 0.18, 0.16, 0.18),
                "correlation_targets": {
                    "CG-001": 0.62, "CG-002": 0.86, "CG-003": 0.85,
                    "CG-004": 0.46, "CG-005": 0.64, "CG-006": 0.50,
                },
                "correlation_drift_speed": 0.02,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.65,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Evidence-C2-014 confidence dropped below 0.80 threshold",
                    },
                    "CLM-T0-003": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — Source-W2-007 offline, "
                            "TTL expired on 2 evidence nodes",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 55, "lag": 4.0, "replays": 1, "nodes_down": 0},
                    "Central": {"skew": 180, "lag": 14.0, "replays": 4, "nodes_down": 2},
                    "West":    {"skew": 55, "lag": 4.5, "replays": 2, "nodes_down": 0},
                },
                "sync_drift_speed": 3.0,
                "integrity_target": 30,
                "confirmation_bonus": 1,
                "ttl_decay_multiplier": 3.0,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "high", "auto_resolved": False},
                    "TTL-BATCH-EXPIRE-T1": {"severity": "medium", "auto_resolved": False},
                },
            },
            # Phase 5: Holds at Elevated Risk (ticks 71+)
            {
                "start": 71, "end": 999,
                "drift_rate": 12,
                "severity_weights": (0.30, 0.30, 0.28, 0.12),
                "category_weights": (0.22, 0.28, 0.18, 0.16, 0.16),
                "correlation_targets": {
                    "CG-001": 0.62, "CG-002": 0.86, "CG-003": 0.85,
                    "CG-004": 0.46, "CG-005": 0.64, "CG-006": 0.50,
                },
                "correlation_drift_speed": 0.01,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.65,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Evidence-C2-014 confidence dropped below 0.80 threshold",
                    },
                    "CLM-T0-003": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — Source-W2-007 offline, "
                            "TTL expired on 2 evidence nodes",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 55, "lag": 4.0, "replays": 1, "nodes_down": 0},
                    "Central": {"skew": 180, "lag": 14.0, "replays": 4, "nodes_down": 2},
                    "West":    {"skew": 55, "lag": 4.5, "replays": 2, "nodes_down": 0},
                },
                "sync_drift_speed": 0.5,
                "integrity_target": 30,
                "confirmation_bonus": 1,
                "ttl_decay_multiplier": 2.5,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "high", "auto_resolved": False},
                    "TTL-BATCH-EXPIRE-T1": {"severity": "medium", "auto_resolved": False},
                },
            },
        ],
    },

    "day3": {
        "description": "External mismatch — critical drift, INVALID correlation, replay flags, potential recovery",
        "phases": [
            # Phase 1: Starting from Day2 end state (ticks 0-10)
            {
                "start": 0, "end": 10,
                "drift_rate": 12,
                "severity_weights": (0.30, 0.30, 0.28, 0.12),
                "category_weights": (0.22, 0.28, 0.18, 0.16, 0.16),
                "correlation_targets": {
                    "CG-001": 0.62, "CG-002": 0.86, "CG-003": 0.85,
                    "CG-004": 0.46, "CG-005": 0.64, "CG-006": 0.50,
                },
                "correlation_drift_speed": 0.02,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.65,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Evidence-C2-014 confidence dropped below 0.80 threshold",
                    },
                    "CLM-T0-003": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — Source-W2-007 offline, "
                            "TTL expired on 2 evidence nodes",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 60, "lag": 5.0, "replays": 1, "nodes_down": 0},
                    "Central": {"skew": 200, "lag": 16.0, "replays": 4, "nodes_down": 2},
                    "West":    {"skew": 60, "lag": 5.0, "replays": 2, "nodes_down": 0},
                },
                "sync_drift_speed": 2.0,
                "integrity_target": 30,
                "confirmation_bonus": 1,
                "ttl_decay_multiplier": 3.0,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "high", "auto_resolved": False},
                    "TTL-BATCH-EXPIRE-T1": {"severity": "medium", "auto_resolved": False},
                },
            },
            # Phase 2: Critical drift injection (ticks 11-30)
            {
                "start": 11, "end": 30,
                "drift_rate": 16,
                "severity_weights": (0.25, 0.28, 0.30, 0.17),
                "category_weights": (0.18, 0.30, 0.15, 0.12, 0.25),
                "correlation_targets": {
                    "CG-001": 0.65, "CG-002": 0.88, "CG-003": 0.92,
                    "CG-004": 0.50, "CG-005": 0.68, "CG-006": 0.55,
                },
                "correlation_drift_speed": 0.04,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 0,
                        "confidence_target": 0.55,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Multiple evidence nodes below confidence threshold — "
                            "quorum margin exhausted",
                    },
                    "CLM-T0-003": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — Source-W2-007 offline, "
                            "TTL expired on 2 evidence nodes",
                    },
                    "CLM-T0-005": {
                        "margin_target": 1,
                        "confidence_target": 0.76,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Cross-region correlation from CG-003 "
                            "degrading Central domain evidence",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 90, "lag": 8.0, "replays": 2, "nodes_down": 1},
                    "Central": {"skew": 350, "lag": 22.0, "replays": 6, "nodes_down": 2},
                    "West":    {"skew": 85, "lag": 7.0, "replays": 3, "nodes_down": 1},
                },
                "sync_drift_speed": 5.0,
                "integrity_target": 22,
                "confirmation_bonus": 0,
                "ttl_decay_multiplier": 4.0,
                "patch_active": False,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "critical", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "critical", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "critical", "auto_resolved": False},
                    "TTL-BATCH-EXPIRE-T1": {"severity": "high", "auto_resolved": False},
                    "TIMING-LAG-WEST": {"severity": "high", "auto_resolved": False},
                },
            },
            # Phase 3: Correlation crosses INVALID, replay flags peak (ticks 31-50)
            {
                "start": 31, "end": 50,
                "drift_rate": 18,
                "severity_weights": (0.20, 0.25, 0.32, 0.23),
                "category_weights": (0.15, 0.32, 0.13, 0.12, 0.28),
                "correlation_targets": {
                    "CG-001": 0.68, "CG-002": 0.92, "CG-003": 0.96,
                    "CG-004": 0.55, "CG-005": 0.72, "CG-006": 0.60,
                },
                "correlation_drift_speed": 0.04,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 0,
                        "confidence_target": 0.45,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — multiple evidence nodes offline "
                            "across Central domain",
                    },
                    "CLM-T0-003": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — Source-W2-007 offline, "
                            "TTL expired on 2 evidence nodes",
                    },
                    "CLM-T0-005": {
                        "margin_target": 0,
                        "confidence_target": 0.60,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": True,
                        "degradation_reason":
                            "Quorum broken — CG-003 correlation invalidated "
                            "3 evidence streams",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 150, "lag": 12.0, "replays": 4, "nodes_down": 1},
                    "Central": {"skew": 500, "lag": 35.0, "replays": 8, "nodes_down": 3},
                    "West":    {"skew": 140, "lag": 10.0, "replays": 5, "nodes_down": 1},
                },
                "sync_drift_speed": 8.0,
                "integrity_target": 24,
                "confirmation_bonus": 0,
                "ttl_decay_multiplier": 5.0,
                "patch_active": False,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "critical", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "critical", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "critical", "auto_resolved": False},
                    "TTL-BATCH-EXPIRE-T1": {"severity": "high", "auto_resolved": False},
                    "TIMING-LAG-WEST": {"severity": "high", "auto_resolved": False},
                },
            },
            # Phase 4: Bottom — index at lowest (ticks 51-70)
            {
                "start": 51, "end": 70,
                "drift_rate": 20,
                "severity_weights": (0.15, 0.22, 0.35, 0.28),
                "category_weights": (0.12, 0.35, 0.13, 0.10, 0.30),
                "correlation_targets": {
                    "CG-001": 0.70, "CG-002": 0.94, "CG-003": 0.97,
                    "CG-004": 0.58, "CG-005": 0.75, "CG-006": 0.62,
                },
                "correlation_drift_speed": 0.02,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — multiple evidence nodes offline "
                            "across Central domain",
                    },
                    "CLM-T0-003": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — Source-W2-007 offline, "
                            "TTL expired on 2 evidence nodes",
                    },
                    "CLM-T0-005": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": True,
                        "degradation_reason":
                            "Quorum broken — CG-003 correlation invalidated "
                            "3 evidence streams",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 200, "lag": 16.0, "replays": 5, "nodes_down": 2},
                    "Central": {"skew": 600, "lag": 40.0, "replays": 10, "nodes_down": 3},
                    "West":    {"skew": 180, "lag": 14.0, "replays": 6, "nodes_down": 1},
                },
                "sync_drift_speed": 5.0,
                "integrity_target": 22,
                "confirmation_bonus": 0,
                "ttl_decay_multiplier": 5.0,
                "patch_active": False,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "critical", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "critical", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "critical", "auto_resolved": False},
                    "TTL-BATCH-EXPIRE-T1": {"severity": "high", "auto_resolved": False},
                    "TIMING-LAG-WEST": {"severity": "high", "auto_resolved": False},
                },
            },
            # Phase 5: Patch begins — partial recovery (ticks 71-90)
            {
                "start": 71, "end": 90,
                "drift_rate": 12,
                "severity_weights": (0.35, 0.30, 0.25, 0.10),
                "category_weights": (0.22, 0.25, 0.18, 0.18, 0.17),
                "correlation_targets": {
                    "CG-001": 0.62, "CG-002": 0.88, "CG-003": 0.88,
                    "CG-004": 0.50, "CG-005": 0.65, "CG-006": 0.52,
                },
                "correlation_drift_speed": 0.03,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.72,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Recovering — evidence nodes coming back online",
                    },
                    "CLM-T0-003": {
                        "margin_target": 0,
                        "confidence_target": None,
                        "status": "UNKNOWN",
                        "correlation_groups_actual": 1,
                        "out_of_band_present": False,
                        "degradation_reason":
                            "Quorum broken — Source-W2-007 recovery pending",
                    },
                    "CLM-T0-005": {
                        "margin_target": 1,
                        "confidence_target": 0.78,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Recovering — independent backup sources activated",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 80, "lag": 6.0, "replays": 2, "nodes_down": 0},
                    "Central": {"skew": 250, "lag": 18.0, "replays": 4, "nodes_down": 1},
                    "West":    {"skew": 70, "lag": 5.0, "replays": 2, "nodes_down": 0},
                },
                "sync_drift_speed": 4.0,
                "integrity_target": 16,
                "confirmation_bonus": 1,
                "ttl_decay_multiplier": 2.0,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CONF-VOLATILITY-C2": {"severity": "high", "auto_resolved": False},
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "high", "auto_resolved": False},
                },
            },
            # Phase 6: Partial stabilization (ticks 91+)
            {
                "start": 91, "end": 999,
                "drift_rate": 8,
                "severity_weights": (0.45, 0.30, 0.18, 0.07),
                "category_weights": (0.28, 0.22, 0.20, 0.18, 0.12),
                "correlation_targets": {
                    "CG-001": 0.58, "CG-002": 0.82, "CG-003": 0.80,
                    "CG-004": 0.44, "CG-005": 0.58, "CG-006": 0.46,
                },
                "correlation_drift_speed": 0.02,
                "claim_effects": {
                    "CLM-T0-002": {
                        "margin_target": 1,
                        "confidence_target": 0.78,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Partially recovered — monitoring for stability",
                    },
                    "CLM-T0-003": {
                        "margin_target": 1,
                        "confidence_target": 0.70,
                        "status": "DEGRADED",
                        "degradation_reason":
                            "Source-W2-007 backup activated — re-establishing quorum",
                    },
                    "CLM-T0-005": {
                        "margin_target": 2,
                        "confidence_target": 0.84,
                        "status": "VERIFIED",
                    },
                },
                "sync_targets": {
                    "East":    {"skew": 40, "lag": 2.5, "replays": 0, "nodes_down": 0},
                    "Central": {"skew": 120, "lag": 8.0, "replays": 2, "nodes_down": 1},
                    "West":    {"skew": 35, "lag": 2.0, "replays": 0, "nodes_down": 0},
                },
                "sync_drift_speed": 3.0,
                "integrity_target": 20,
                "confirmation_bonus": 2,
                "ttl_decay_multiplier": 1.5,
                "patch_active": True,
                "fingerprint_escalation": {
                    "CORR-DRIFT-S003": {"severity": "high", "auto_resolved": False},
                    "SYNC-BEACON-SKEW": {"severity": "medium", "auto_resolved": True},
                },
            },
        ],
    },
}
