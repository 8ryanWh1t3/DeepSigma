from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional

from .clustering import cluster_signals
from .falsification import build_discriminating_evidence_plan
from .ids import stable_id
from .lifecycle import transition
from .models import (
    AltCogCandidatePacket,
    AlternativeKind,
    DiscriminatingEvidencePlan,
    DiscoveryEvent,
    DiscoverySurface,
    DormantAlternativeMonitor,
    EvidenceItem,
    ExceptionClusterCard,
    FrictionSignalRecord,
    MaturityState,
    Prediction,
    ProvenanceRef,
    ResidualEvidenceRecord,
    ValidationResult,
)
from .monitoring import make_dormant_monitor, should_reactivate
from .provenance import AuditLedger
from .scoring import PromotionPolicy, operational_readiness, score_candidate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AltCogEngine:
    """Stateful convenience façade around deterministic AltCogOps primitives."""

    def __init__(self, *, promotion_policy: PromotionPolicy | None = None) -> None:
        self.promotion_policy = promotion_policy or PromotionPolicy()
        self.ledger = AuditLedger()

    def capture_friction(
        self,
        *,
        stream_id: str,
        surface: DiscoverySurface,
        statement: str,
        source: str,
        detected_at: str | None = None,
        strength: float = 0.5,
        tags: Iterable[str] = (),
        domain: str = "",
        provenance: Iterable[ProvenanceRef] = (),
    ) -> FrictionSignalRecord:
        detected_at = detected_at or _now()
        strength = max(0.0, min(1.0, float(strength)))
        payload = {
            "stream_id": stream_id,
            "surface": surface.value,
            "statement": statement,
            "source": source,
            "detected_at": detected_at,
        }
        signal = FrictionSignalRecord(
            id=stable_id("FSR", payload),
            stream_id=stream_id,
            surface=surface,
            statement=statement,
            source=source,
            detected_at=detected_at,
            maturity=MaturityState.AC2_WEAK_SIGNAL if strength >= 0.6 else MaturityState.AC1_ANOMALY,
            strength=strength,
            tags=sorted(set(tags)),
            domain=domain,
            provenance=list(provenance),
        )
        event_type = (
            DiscoveryEvent.E13_OUTCOME_MISMATCH_DETECTED.value
            if surface == DiscoverySurface.OUTCOME_MISMATCH
            else "FRICTION_SIGNAL_CAPTURED"
        )
        self.ledger.append(event_type=event_type, occurred_at=detected_at, subject_id=signal.id, payload=payload)
        return signal

    def capture_residual(
        self,
        *,
        stream_id: str,
        dominant_model: str,
        observed: str,
        explained: str,
        residual: str,
        source: str,
        detected_at: str | None = None,
    ) -> tuple[ResidualEvidenceRecord, FrictionSignalRecord]:
        detected_at = detected_at or _now()
        record_payload = {
            "stream_id": stream_id,
            "dominant_model": dominant_model,
            "observed": observed,
            "residual": residual,
        }
        signal = self.capture_friction(
            stream_id=stream_id,
            surface=DiscoverySurface.RESIDUAL_EVIDENCE,
            statement=residual,
            source=source,
            detected_at=detected_at,
            strength=0.7,
            tags=["residual"],
        )
        record = ResidualEvidenceRecord(
            id=stable_id("RER", record_payload),
            stream_id=stream_id,
            dominant_model=dominant_model,
            observed=observed,
            explained=explained,
            residual=residual,
            detected_at=detected_at,
            signal_id=signal.id,
        )
        self.ledger.append(
            event_type=DiscoveryEvent.E14_RESIDUAL_EVIDENCE_IDENTIFIED.value,
            occurred_at=detected_at,
            subject_id=record.id,
            payload={"signal_id": signal.id, "dominant_model": dominant_model},
        )
        return record, signal

    def cluster(
        self,
        signals: Iterable[FrictionSignalRecord],
        *,
        min_similarity: float = 0.25,
        created_at: str | None = None,
    ) -> List[ExceptionClusterCard]:
        created_at = created_at or _now()
        cards = cluster_signals(signals, min_similarity=min_similarity, created_at=created_at)
        for card in cards:
            if len(card.signal_ids) > 1:
                self.ledger.append(
                    event_type=DiscoveryEvent.E15_EXCEPTION_PATTERN_FORMED.value,
                    occurred_at=created_at,
                    subject_id=card.id,
                    payload={"signal_ids": card.signal_ids},
                )
        return cards

    def create_candidate(
        self,
        *,
        cluster: ExceptionClusterCard,
        dominant_model: str,
        hypothesis: str,
        prediction: Prediction | None = None,
        predictions: Iterable[Prediction] = (),
        kind: AlternativeKind = AlternativeKind.STRUCTURAL,
        evidence: Iterable[EvidenceItem] = (),
        falsification_conditions: Iterable[str] = (),
        mission_relevance: float = 0.0,
        owner: str = "",
        revisit_trigger: str = "",
        created_at: str | None = None,
    ) -> AltCogCandidatePacket:
        created_at = created_at or _now()
        all_predictions = list(predictions)
        if prediction is not None:
            all_predictions.insert(0, prediction)
        conditions = list(falsification_conditions)
        if not conditions and all_predictions:
            conditions = [
                f"Alternative is weakened if observation of '{all_predictions[0].variable}' "
                f"matches dominant expectation '{all_predictions[0].dominant_expected}'."
            ]
        payload = {
            "cluster_id": cluster.id,
            "dominant_model": dominant_model,
            "hypothesis": hypothesis,
            "created_at": created_at,
        }
        candidate = AltCogCandidatePacket(
            id=stable_id("ACP", payload),
            stream_id=cluster.stream_id,
            cluster_id=cluster.id,
            dominant_model=dominant_model,
            hypothesis=hypothesis,
            created_at=created_at,
            kind=kind,
            signal_ids=list(cluster.signal_ids),
            evidence=list(evidence),
            predictions=all_predictions,
            falsification_conditions=conditions,
            mission_relevance=max(0.0, min(1.0, mission_relevance)),
            owner=owner,
            revisit_trigger=revisit_trigger,
        )
        self.ledger.append(
            event_type=DiscoveryEvent.E16_ALTCOG_CANDIDATE_CREATED.value,
            occurred_at=created_at,
            subject_id=candidate.id,
            payload={"cluster_id": cluster.id, "dominant_model": dominant_model},
        )
        return candidate

    def score(self, candidate: AltCogCandidatePacket) -> AltCogCandidatePacket:
        candidate.score = score_candidate(candidate)
        if candidate.maturity == MaturityState.AC4_ALTERNATIVE_HYPOTHESIS:
            transition(candidate, MaturityState.AC5_SCORED_ALTERNATIVE)
        self.ledger.append(
            event_type="ALTERNATIVE_SCORED",
            occurred_at=_now(),
            subject_id=candidate.id,
            payload={"total": candidate.score.total},
        )
        return candidate

    def readiness(self, candidate: AltCogCandidatePacket) -> tuple[bool, list[str]]:
        return operational_readiness(candidate, self.promotion_policy)

    def promote_if_ready(self, candidate: AltCogCandidatePacket) -> AltCogCandidatePacket:
        ready, reasons = self.readiness(candidate)
        if not ready:
            candidate.metadata["promotion_blockers"] = reasons
            return candidate
        if candidate.maturity == MaturityState.AC5_SCORED_ALTERNATIVE:
            transition(candidate, MaturityState.AC6_OPERATIONAL_ALTERNATIVE)
            self.ledger.append(
                event_type=DiscoveryEvent.E17_CANDIDATE_PROMOTED_OPERATIONAL.value,
                occurred_at=_now(),
                subject_id=candidate.id,
                payload={"score": candidate.score.total if candidate.score else None},
            )
        candidate.metadata.pop("promotion_blockers", None)
        return candidate

    def plan(self, candidate: AltCogCandidatePacket, *, due_at: str = "") -> DiscriminatingEvidencePlan:
        return build_discriminating_evidence_plan(candidate, created_at=_now(), due_at=due_at)

    def validate(
        self,
        candidate: AltCogCandidatePacket,
        *,
        verdict: str,
        rationale: str,
        evidence_ids: Iterable[str] = (),
        confidence: float = 0.0,
        observed_at: str | None = None,
    ) -> AltCogCandidatePacket:
        if candidate.maturity != MaturityState.AC6_OPERATIONAL_ALTERNATIVE:
            raise ValueError("Validation requires AC6 Operational Alternative")
        observed_at = observed_at or _now()
        result = ValidationResult(
            candidate_id=candidate.id,
            observed_at=observed_at,
            verdict=verdict,
            rationale=rationale,
            evidence_ids=list(evidence_ids),
            confidence=max(0.0, min(1.0, confidence)),
        )
        candidate.validation = result
        if verdict == "alternative_supported":
            transition(candidate, MaturityState.AC7_PROMOTED_MODEL)
        elif verdict == "dominant_supported":
            candidate.archived_reason = "Validation favored dominant model"
            transition(candidate, MaturityState.AC8_ARCHIVED_WITH_TRIGGER)
        elif verdict != "inconclusive":
            raise ValueError("verdict must be alternative_supported, dominant_supported, or inconclusive")
        self.ledger.append(
            event_type="ALTERNATIVE_VALIDATED",
            occurred_at=observed_at,
            subject_id=candidate.id,
            payload={"verdict": verdict, "confidence": result.confidence},
        )
        return candidate

    def archive(
        self,
        candidate: AltCogCandidatePacket,
        *,
        reason: str,
        archived_at: str | None = None,
        trigger_terms: Iterable[str] = (),
    ) -> tuple[AltCogCandidatePacket, DormantAlternativeMonitor]:
        archived_at = archived_at or _now()
        if candidate.maturity != MaturityState.AC8_ARCHIVED_WITH_TRIGGER:
            transition(candidate, MaturityState.AC8_ARCHIVED_WITH_TRIGGER)
        candidate.archived_reason = reason
        monitor = make_dormant_monitor(candidate, archived_at=archived_at, trigger_terms=trigger_terms)
        self.ledger.append(
            event_type="ALTERNATIVE_ARCHIVED",
            occurred_at=archived_at,
            subject_id=candidate.id,
            payload={"reason": reason, "monitor_id": monitor.id},
        )
        return candidate, monitor

    def reactivate(
        self,
        candidate: AltCogCandidatePacket,
        monitor: DormantAlternativeMonitor,
        signals: Iterable[FrictionSignalRecord],
        *,
        reactivated_at: str | None = None,
    ) -> tuple[AltCogCandidatePacket, DormantAlternativeMonitor, list[str]]:
        should, hits = should_reactivate(monitor, signals)
        if not should:
            return candidate, monitor, hits
        if candidate.maturity != MaturityState.AC8_ARCHIVED_WITH_TRIGGER:
            raise ValueError("Only AC8 candidates can be reactivated")
        transition(candidate, MaturityState.AC4_ALTERNATIVE_HYPOTHESIS)
        candidate.score = None
        candidate.validation = None
        monitor.active = False
        monitor.reactivated_at = reactivated_at or _now()
        self.ledger.append(
            event_type=DiscoveryEvent.E18_DORMANT_ALTERNATIVE_REACTIVATED.value,
            occurred_at=monitor.reactivated_at,
            subject_id=candidate.id,
            payload={"monitor_id": monitor.id, "trigger_hits": hits},
        )
        return candidate, monitor, hits
