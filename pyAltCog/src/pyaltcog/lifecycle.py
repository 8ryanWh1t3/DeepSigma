from __future__ import annotations

from .models import AltCogCandidatePacket, MaturityState


class LifecycleError(ValueError):
    pass


_ALLOWED = {
    MaturityState.AC0_NOISE: {MaturityState.AC1_ANOMALY},
    MaturityState.AC1_ANOMALY: {MaturityState.AC2_WEAK_SIGNAL, MaturityState.AC8_ARCHIVED_WITH_TRIGGER},
    MaturityState.AC2_WEAK_SIGNAL: {MaturityState.AC3_CANDIDATE_PATTERN, MaturityState.AC8_ARCHIVED_WITH_TRIGGER},
    MaturityState.AC3_CANDIDATE_PATTERN: {MaturityState.AC4_ALTERNATIVE_HYPOTHESIS, MaturityState.AC8_ARCHIVED_WITH_TRIGGER},
    MaturityState.AC4_ALTERNATIVE_HYPOTHESIS: {MaturityState.AC5_SCORED_ALTERNATIVE, MaturityState.AC8_ARCHIVED_WITH_TRIGGER},
    MaturityState.AC5_SCORED_ALTERNATIVE: {MaturityState.AC6_OPERATIONAL_ALTERNATIVE, MaturityState.AC8_ARCHIVED_WITH_TRIGGER},
    MaturityState.AC6_OPERATIONAL_ALTERNATIVE: {MaturityState.AC7_PROMOTED_MODEL, MaturityState.AC8_ARCHIVED_WITH_TRIGGER},
    MaturityState.AC7_PROMOTED_MODEL: {MaturityState.AC8_ARCHIVED_WITH_TRIGGER},
    MaturityState.AC8_ARCHIVED_WITH_TRIGGER: {MaturityState.AC4_ALTERNATIVE_HYPOTHESIS},
}


def can_transition(current: MaturityState, target: MaturityState) -> bool:
    return target in _ALLOWED.get(current, set())


def transition(candidate: AltCogCandidatePacket, target: MaturityState) -> AltCogCandidatePacket:
    if not can_transition(candidate.maturity, target):
        raise LifecycleError(f"Invalid AltCog transition: {candidate.maturity.value} -> {target.value}")
    candidate.maturity = target
    return candidate
