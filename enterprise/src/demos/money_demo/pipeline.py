"""Money Demo pipeline — 10-step end-to-end domain mode exercise.

Steps:
1. LOAD — load fixture records + claims
2. INTELOPS INGEST — claim loop (ingest all baseline claims)
3. INTELOPS VALIDATE — validate all claims
4. INTELOPS DELTA — ingest contradicting delta claim, detect drift
5. FRANOPS PROPOSE — propose canon entries from validated claims
6. FRANOPS RETCON — assess and execute retcon from contradiction
7. REOPS EPISODE — begin, gate, non-coercion, seal episode
8. CASCADE — propagate retcon through cascade engine
9. COHERENCE — run coherence check, severity scoring
10. SEAL — compute summary with before/after metrics
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modes.intelops import IntelOps
from core.modes.franops import FranOps
from core.modes.reflectionops import ReflectionOps
from core.modes.cascade import CascadeEngine
from core.memory_graph import MemoryGraph
from core.drift_signal import DriftSignalCollector
from core.episode_state import EpisodeTracker
from core.feeds.canon.workflow import CanonWorkflow
from core.audit_log import AuditLog


@dataclass
class MoneyDemoResult:
    """Result of the money demo pipeline."""

    steps: List[Dict[str, Any]] = field(default_factory=list)
    baseline_claims: int = 0
    delta_claims: int = 0
    drift_signals_total: int = 0
    retcon_executed: bool = False
    cascade_rules_triggered: int = 0
    coherence_score: float = 0.0
    episode_sealed: bool = False
    audit_entries: int = 0
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": self.steps,
            "baselineClaims": self.baseline_claims,
            "deltaClaims": self.delta_claims,
            "driftSignalsTotal": self.drift_signals_total,
            "retconExecuted": self.retcon_executed,
            "cascadeRulesTriggered": self.cascade_rules_triggered,
            "coherenceScore": self.coherence_score,
            "episodeSealed": self.episode_sealed,
            "auditEntries": self.audit_entries,
            "elapsedMs": self.elapsed_ms,
        }


def load_fixtures(fixture_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load baseline and delta fixture data."""
    if fixture_dir is None:
        fixture_dir = Path(__file__).parent / "fixtures"
    else:
        fixture_dir = Path(fixture_dir)

    baseline = json.loads((fixture_dir / "baseline.json").read_text(encoding="utf-8"))
    delta = json.loads((fixture_dir / "delta.json").read_text(encoding="utf-8"))
    return {"baseline": baseline, "delta": delta}


def run_pipeline(fixture_dir: Optional[str | Path] = None) -> MoneyDemoResult:
    """Execute the 10-step money demo pipeline.

    Returns a MoneyDemoResult with metrics from each step.
    """
    t0 = time.monotonic()
    result = MoneyDemoResult()

    # Initialize domain modes
    intel = IntelOps()
    fran = FranOps()
    reops = ReflectionOps()

    # Initialize cascade engine
    cascade = CascadeEngine()
    cascade.register_domain(intel)
    cascade.register_domain(fran)
    cascade.register_domain(reops)

    # Shared context
    mg = MemoryGraph()
    ds = DriftSignalCollector()
    tracker = EpisodeTracker()
    workflow = CanonWorkflow()
    audit_log = AuditLog()

    ctx: Dict[str, Any] = {
        "memory_graph": mg,
        "drift_collector": ds,
        "canon_store": None,
        "canon_claims": [],
        "claims": {},
        "all_claims": [],
        "all_canon_entries": [],
        "workflow": workflow,
        "episode_tracker": tracker,
        "audit_log": audit_log,
        "gates": [],
        "blessed_claims": set(),
        "now": datetime(2026, 2, 28, tzinfo=timezone.utc),
    }

    # ── Step 1: LOAD ─────────────────────────────────────────────
    fixtures = load_fixtures(fixture_dir)
    baseline_claims = fixtures["baseline"]["claims"]
    delta_claims = fixtures["delta"]["claims"]
    result.baseline_claims = len(baseline_claims)
    result.delta_claims = len(delta_claims)
    result.steps.append({"step": "LOAD", "status": "ok", "claims": len(baseline_claims) + len(delta_claims)})

    # ── Step 2: INTELOPS INGEST ──────────────────────────────────
    ingest_results = []
    for claim in baseline_claims:
        r = intel.handle("INTEL-F01", {"payload": claim}, ctx)
        ingest_results.append(r)
        ctx["claims"][claim["claimId"]] = claim
        ctx["all_claims"].append(claim)
    result.steps.append({"step": "INTELOPS_INGEST", "status": "ok", "ingested": len(ingest_results)})

    # ── Step 3: INTELOPS VALIDATE ────────────────────────────────
    validate_results = []
    for claim in baseline_claims:
        r = intel.handle("INTEL-F02", {"payload": {"claimId": claim["claimId"]}}, ctx)
        validate_results.append(r)
    total_drift = sum(len(r.drift_signals) for r in validate_results)
    result.steps.append({"step": "INTELOPS_VALIDATE", "status": "ok", "driftSignals": total_drift})

    # ── Step 4: INTELOPS DELTA ───────────────────────────────────
    delta_drift = 0
    for claim in delta_claims:
        # Ingest the contradicting claim
        intel.handle("INTEL-F01", {"payload": claim}, ctx)
        ctx["claims"][claim["claimId"]] = claim
        ctx["all_claims"].append(claim)

        # Update canon claims for contradiction detection
        ctx["canon_claims"] = [c for c in baseline_claims if c.get("claimId")]

        # Validate - should detect contradiction
        r = intel.handle("INTEL-F02", {"payload": {"claimId": claim["claimId"]}}, ctx)
        delta_drift += len(r.drift_signals)

        # Record drift
        if r.drift_signals:
            intel.handle("INTEL-F03", {"payload": {"drift_signals": r.drift_signals}}, ctx)

    result.drift_signals_total = total_drift + delta_drift
    result.steps.append({"step": "INTELOPS_DELTA", "status": "ok", "contradictions": delta_drift})

    # ── Step 5: FRANOPS PROPOSE ──────────────────────────────────
    for claim in baseline_claims:
        fran.handle("FRAN-F01", {"payload": {
            "canonId": f"CANON-{claim['claimId']}",
            "title": claim["statement"],
            "claimIds": [claim["claimId"]],
        }}, ctx)
        # Bless and activate
        fran.handle("FRAN-F02", {"payload": {
            "canonId": f"CANON-{claim['claimId']}",
            "blessedBy": "money-demo",
        }}, ctx)
    result.steps.append({"step": "FRANOPS_PROPOSE", "status": "ok", "entries": len(baseline_claims)})

    # ── Step 6: FRANOPS RETCON ───────────────────────────────────
    # Retcon the contradicted claim
    r_assess = fran.handle("FRAN-F04", {"payload": {
        "originalClaimId": "CLAIM-MONEY-002",
        "dependents": [],
    }}, ctx)

    r_exec = fran.handle("FRAN-F05", {"payload": {
        "originalClaimId": "CLAIM-MONEY-002",
        "newClaimId": "CLAIM-MONEY-004",
        "reason": "Churn model v3 underperforms on 2026 data (78% vs 92%)",
    }}, ctx)
    result.retcon_executed = r_exec.success
    result.drift_signals_total += len(r_exec.drift_signals)
    result.steps.append({"step": "FRANOPS_RETCON", "status": "ok", "retconExecuted": r_exec.success})

    # ── Step 7: REOPS EPISODE ────────────────────────────────────
    ep_id = "EP-MONEY-DEMO"
    reops.handle("RE-F01", {"payload": {"episodeId": ep_id, "decisionType": "retcon"}}, ctx)
    reops.handle("RE-F04", {"payload": {"episodeId": ep_id, "gateContext": {}}}, ctx)
    reops.handle("RE-F07", {"payload": {"episodeId": ep_id}}, ctx)
    r_seal = reops.handle("RE-F02", {"payload": {"episodeId": ep_id}}, ctx)
    result.episode_sealed = r_seal.success
    result.steps.append({"step": "REOPS_EPISODE", "status": "ok", "sealed": r_seal.success})

    # ── Step 8: CASCADE ──────────────────────────────────────────
    # Propagate the retcon event through cascades
    cascade_result = cascade.propagate(
        "franops",
        {"subtype": "retcon_executed", "payload": {
            "episodeId": f"EP-{ep_id}-cascade",
            "decisionType": "cascade",
        }},
        ctx,
        max_depth=2,
    )
    result.cascade_rules_triggered = cascade_result.total_triggered
    result.steps.append({
        "step": "CASCADE",
        "status": "ok",
        "rulesTriggered": cascade_result.total_triggered,
    })

    # ── Step 9: COHERENCE ────────────────────────────────────────
    r_severity = reops.handle("RE-F08", {"payload": {
        "driftType": "authority_mismatch", "severity": "yellow",
    }}, ctx)

    # Compute coherence based on drift count
    drift_count = ds.event_count if ds.event_count > 0 else result.drift_signals_total
    if drift_count == 0:
        coherence = 95.0
    elif drift_count <= 3:
        coherence = 75.0
    else:
        coherence = 50.0
    ctx["coherence_score"] = coherence

    r_coherence = reops.handle("RE-F09", {"payload": {"episodeId": ep_id}}, ctx)
    result.coherence_score = coherence
    result.steps.append({"step": "COHERENCE", "status": "ok", "score": coherence})

    # ── Step 10: SEAL ────────────────────────────────────────────
    result.audit_entries = audit_log.entry_count
    result.elapsed_ms = (time.monotonic() - t0) * 1000
    result.steps.append({
        "step": "SEAL",
        "status": "ok",
        "auditEntries": audit_log.entry_count,
        "chainValid": audit_log.verify_chain(),
        "elapsedMs": result.elapsed_ms,
    })

    return result
