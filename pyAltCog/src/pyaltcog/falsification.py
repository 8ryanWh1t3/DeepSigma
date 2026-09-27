from __future__ import annotations

from typing import Iterable, List

from .ids import stable_id
from .models import (
    AltCogCandidatePacket,
    DiscriminatingEvidencePlan,
    EvidenceRequest,
    Prediction,
)


def build_discriminating_evidence_plan(
    candidate: AltCogCandidatePacket,
    *,
    created_at: str,
    due_at: str = "",
) -> DiscriminatingEvidencePlan:
    requests: List[EvidenceRequest] = []
    for index, p in enumerate(candidate.predictions, start=1):
        decision_rule = p.success_condition or (
            f"Observe '{p.variable}': evidence closer to '{p.alternative_expected}' supports the alternative; "
            f"evidence closer to '{p.dominant_expected}' supports the dominant model."
        )
        payload = {
            "candidate_id": candidate.id,
            "variable": p.variable,
            "dominant": p.dominant_expected,
            "alternative": p.alternative_expected,
        }
        requests.append(
            EvidenceRequest(
                id=stable_id("REQ", payload),
                variable=p.variable,
                request=f"Collect discriminating observation for {p.variable}",
                dominant_prediction=p.dominant_expected,
                alternative_prediction=p.alternative_expected,
                decision_rule=decision_rule,
                priority=index,
            )
        )
    falsification = (
        candidate.falsification_conditions[0]
        if candidate.falsification_conditions
        else "No falsification condition declared"
    )
    return DiscriminatingEvidencePlan(
        id=stable_id("DEP", {"candidate_id": candidate.id, "requests": [r.id for r in requests]}),
        candidate_id=candidate.id,
        created_at=created_at,
        requests=requests,
        falsification_condition=falsification,
        owner=candidate.owner,
        due_at=due_at,
    )
