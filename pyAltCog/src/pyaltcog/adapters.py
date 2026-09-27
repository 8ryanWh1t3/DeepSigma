from __future__ import annotations

from typing import Any, Dict, List

from .models import AltCogCandidatePacket, DiscriminatingEvidencePlan
from .serde import to_primitive


def to_cerpa(candidate: AltCogCandidatePacket) -> Dict[str, Any]:
    return {
        "kind": "ALTCOG_REVIEW_INPUT",
        "claim": candidate.dominant_model,
        "event": candidate.hypothesis,
        "review": {
            "candidate_id": candidate.id,
            "maturity": candidate.maturity.value,
            "score": candidate.score.total if candidate.score else None,
        },
        "patch_hint": "reassess dominant model if validation supports alternative",
    }


def to_dko(candidate: AltCogCandidatePacket, plan: DiscriminatingEvidencePlan | None = None) -> Dict[str, Any]:
    return {
        "object_type": "AlternativeCognition",
        "identity": candidate.id,
        "state": candidate.maturity.value,
        "semantic": {
            "dominant_model": candidate.dominant_model,
            "alternative_hypothesis": candidate.hypothesis,
        },
        "governance": {
            "owner": candidate.owner,
            "revisit_trigger": candidate.revisit_trigger,
        },
        "evidence": [to_primitive(e) for e in candidate.evidence],
        "plan": to_primitive(plan) if plan else None,
    }


def to_resonator(candidate: AltCogCandidatePacket) -> Dict[str, Any]:
    return {
        "case_type": "dominant_vs_alternative",
        "candidate_id": candidate.id,
        "left": candidate.dominant_model,
        "right": candidate.hypothesis,
        "predictions": [to_primitive(p) for p in candidate.predictions],
        "falsification_conditions": list(candidate.falsification_conditions),
    }


def to_pathfinder(candidate: AltCogCandidatePacket) -> List[Dict[str, str]]:
    edges = [{"subject": candidate.id, "predicate": "challenges", "object": candidate.dominant_model}]
    for sid in candidate.signal_ids:
        edges.append({"subject": sid, "predicate": "supportsAlternative", "object": candidate.id})
    if candidate.owner:
        edges.append({"subject": candidate.id, "predicate": "ownedBy", "object": candidate.owner})
    return edges


def to_intelops(candidate: AltCogCandidatePacket) -> Dict[str, Any]:
    return {
        "claim": candidate.hypothesis,
        "confidence": candidate.score.evidence if candidate.score else 0.0,
        "contradicts_or_challenges": candidate.dominant_model,
        "evidence_ids": [e.id for e in candidate.evidence],
        "revalidation_trigger": candidate.revisit_trigger,
    }


def to_reops(candidate: AltCogCandidatePacket) -> Dict[str, Any]:
    return {
        "decision_input_type": "alternative_model",
        "candidate_id": candidate.id,
        "status": candidate.maturity.value,
        "owner": candidate.owner,
        "why": candidate.hypothesis,
        "kill_switch_or_revisit": candidate.revisit_trigger,
    }


def to_franops(candidate: AltCogCandidatePacket) -> Dict[str, Any]:
    return {
        "canon_change_candidate": candidate.id,
        "current_canon_or_model": candidate.dominant_model,
        "proposed_model": candidate.hypothesis,
        "requires_validation": candidate.maturity.value != "AC7",
    }
