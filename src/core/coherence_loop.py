"""Coherence Loop — orchestrates the five-primitive CERPA sequence.

Wraps the CERPA engine to process primitives through the full
CLAIM -> EVENT -> REVIEW -> PATCH -> APPLY sequence, producing
PrimitiveEnvelopes at each step.

Usage:
    result = run_coherence_loop(claim_payload, event_payload, source="my-module")
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .cerpa.engine import (
    apply_patch,
    generate_patch_from_review,
    review_claim_against_event,
)
from .cerpa.models import Claim, Event
from .primitive_envelope import PrimitiveEnvelope, wrap_primitive
from .primitives import PrimitiveType


class CoherenceStep(str, Enum):
    """Steps in the coherence loop — mirrors PrimitiveType."""

    CLAIM = "claim"
    EVENT = "event"
    REVIEW = "review"
    PATCH = "patch"
    APPLY = "apply"


@dataclass
class StepRecord:
    """Record of a single step in the coherence loop."""

    step: CoherenceStep
    envelope: PrimitiveEnvelope
    duration_ms: float
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step.value,
            "envelope": self.envelope.to_dict(),
            "durationMs": self.duration_ms,
            "notes": self.notes,
        }


@dataclass
class CoherenceLoopResult:
    """Result of a complete coherence loop run."""

    loop_id: str
    steps: List[StepRecord]
    completed: bool
    halted_at: Optional[CoherenceStep] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "loopId": self.loop_id,
            "steps": [s.to_dict() for s in self.steps],
            "completed": self.completed,
        }
        if self.halted_at is not None:
            d["haltedAt"] = self.halted_at.value
        if self.metadata:
            d["metadata"] = self.metadata
        return d


def _loop_id() -> str:
    return f"LOOP-{uuid.uuid4().hex[:8]}"


def _timed(fn, *args, **kwargs):
    """Call *fn* and return (result, duration_ms)."""
    t0 = time.monotonic()
    result = fn(*args, **kwargs)
    elapsed = (time.monotonic() - t0) * 1000
    return result, elapsed


def run_coherence_loop(
    claim_payload: Dict[str, Any],
    event_payload: Dict[str, Any],
    source: str = "coherence-loop",
) -> CoherenceLoopResult:
    """Run a complete coherence loop through CERPA.

    1. Wrap claim payload as CLAIM envelope
    2. Wrap event payload as EVENT envelope
    3. Review claim against event -> REVIEW envelope
    4. If drift detected, generate patch -> PATCH envelope
    5. If patch generated, apply patch -> APPLY envelope

    Returns a CoherenceLoopResult with all step records.
    """
    loop_id = _loop_id()
    steps: List[StepRecord] = []

    # 1. CLAIM
    t0 = time.monotonic()
    claim_env = wrap_primitive(PrimitiveType.CLAIM.value, claim_payload, source)
    claim_ms = (time.monotonic() - t0) * 1000
    steps.append(StepRecord(
        step=CoherenceStep.CLAIM,
        envelope=claim_env,
        duration_ms=round(claim_ms, 3),
    ))

    # Build CERPA Claim object from payload
    claim_obj = Claim(
        id=claim_payload.get("id", claim_env.envelope_id),
        text=claim_payload.get("text", ""),
        domain=claim_payload.get("domain", "default"),
        source=claim_payload.get("source", source),
        timestamp=claim_payload.get("timestamp", claim_env.created_at),
        assumptions=claim_payload.get("assumptions", []),
        metadata=claim_payload.get("metadata", {}),
    )

    # 2. EVENT
    t0 = time.monotonic()
    event_env = wrap_primitive(PrimitiveType.EVENT.value, event_payload, source)
    event_ms = (time.monotonic() - t0) * 1000
    steps.append(StepRecord(
        step=CoherenceStep.EVENT,
        envelope=event_env,
        duration_ms=round(event_ms, 3),
    ))

    # Build CERPA Event object from payload
    event_obj = Event(
        id=event_payload.get("id", event_env.envelope_id),
        text=event_payload.get("text", ""),
        domain=event_payload.get("domain", "default"),
        source=event_payload.get("source", source),
        timestamp=event_payload.get("timestamp", event_env.created_at),
        observed_state=event_payload.get("observed_state", {}),
        metadata=event_payload.get("metadata", {}),
    )

    # 3. REVIEW
    review_obj, review_ms = _timed(review_claim_against_event, claim_obj, event_obj)
    review_env = wrap_primitive(
        PrimitiveType.REVIEW.value, review_obj.to_dict(), source,
    )
    steps.append(StepRecord(
        step=CoherenceStep.REVIEW,
        envelope=review_env,
        duration_ms=round(review_ms, 3),
        notes=[f"verdict={review_obj.verdict}"],
    ))

    # 4. PATCH (only if drift detected)
    if review_obj.drift_detected:
        patch_obj, patch_ms = _timed(generate_patch_from_review, review_obj)
        if patch_obj is not None:
            patch_env = wrap_primitive(
                PrimitiveType.PATCH.value, patch_obj.to_dict(), source,
            )
            steps.append(StepRecord(
                step=CoherenceStep.PATCH,
                envelope=patch_env,
                duration_ms=round(patch_ms, 3),
                notes=[f"action={patch_obj.action}"],
            ))

            # 5. APPLY
            apply_obj, apply_ms = _timed(apply_patch, patch_obj, claim_obj)
            apply_env = wrap_primitive(
                PrimitiveType.APPLY.value, apply_obj.to_dict(), source,
            )
            steps.append(StepRecord(
                step=CoherenceStep.APPLY,
                envelope=apply_env,
                duration_ms=round(apply_ms, 3),
                notes=[f"success={apply_obj.success}"],
            ))

    return CoherenceLoopResult(
        loop_id=loop_id,
        steps=steps,
        completed=True,
    )
