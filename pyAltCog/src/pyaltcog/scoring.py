from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .models import AltCogCandidatePacket, CandidateScore


@dataclass(frozen=True)
class PromotionPolicy:
    minimum_total: float = 0.70
    minimum_mission_relevance: float = 0.50
    minimum_evidence_confidence: float = 0.40


_WEIGHTS = {
    "evidence": 0.24,
    "distinct_prediction": 0.16,
    "falsifiability": 0.16,
    "mission_relevance": 0.16,
    "contradiction_resilience": 0.10,
    "ownership": 0.09,
    "revisitability": 0.09,
}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def score_candidate(candidate: AltCogCandidatePacket) -> CandidateScore:
    if candidate.evidence:
        weighted = [e.confidence for e in candidate.evidence if e.supports_alternative]
        evidence = sum(weighted) / len(weighted) if weighted else 0.0
    else:
        evidence = 0.0

    distinct_prediction = 1.0 if any(
        p.dominant_expected.strip() and p.alternative_expected.strip()
        and p.dominant_expected.strip().lower() != p.alternative_expected.strip().lower()
        for p in candidate.predictions
    ) else 0.0

    falsifiability = 1.0 if candidate.falsification_conditions else 0.0
    mission_relevance = _clamp(candidate.mission_relevance)
    contradiction_resilience = _clamp(float(candidate.metadata.get("contradiction_resilience", 0.5)))
    ownership = 1.0 if candidate.owner.strip() else 0.0
    revisitability = 1.0 if candidate.revisit_trigger.strip() else 0.0

    parts = {
        "evidence": _clamp(evidence),
        "distinct_prediction": distinct_prediction,
        "falsifiability": falsifiability,
        "mission_relevance": mission_relevance,
        "contradiction_resilience": contradiction_resilience,
        "ownership": ownership,
        "revisitability": revisitability,
    }
    total = sum(parts[k] * _WEIGHTS[k] for k in parts)
    rationale = [f"{k}={parts[k]:.2f} × {_WEIGHTS[k]:.2f}" for k in parts]
    return CandidateScore(total=round(total, 6), rationale=rationale, **parts)


def operational_readiness(
    candidate: AltCogCandidatePacket,
    policy: PromotionPolicy = PromotionPolicy(),
) -> Tuple[bool, list[str]]:
    reasons: list[str] = []
    if not candidate.dominant_model.strip():
        reasons.append("dominant model missing")
    if not candidate.signal_ids:
        reasons.append("no supporting signals")
    if not candidate.predictions:
        reasons.append("no distinct prediction")
    elif not any(p.dominant_expected != p.alternative_expected for p in candidate.predictions):
        reasons.append("prediction does not discriminate")
    if not candidate.falsification_conditions:
        reasons.append("falsification condition missing")
    if candidate.mission_relevance < policy.minimum_mission_relevance:
        reasons.append("mission relevance below threshold")
    if not candidate.owner.strip():
        reasons.append("owner missing")
    if not candidate.revisit_trigger.strip():
        reasons.append("revisit trigger missing")
    if candidate.score is None:
        reasons.append("candidate not scored")
    else:
        if candidate.score.total < policy.minimum_total:
            reasons.append("total score below threshold")
        if candidate.score.evidence < policy.minimum_evidence_confidence:
            reasons.append("evidence confidence below threshold")
    return (not reasons), reasons
