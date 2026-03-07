"""Mock adapter — deterministic output for tests and demos."""

from __future__ import annotations

import hashlib
from typing import Any, Dict

from ..base_adapter import BaseModelAdapter
from ..models import (
    CandidateClaim,
    ModelMeta,
    ReasoningResult,
    ReasoningStep,
)
from ..ttl import compute_claim_ttl_seconds, ttl_from_packet


class MockAdapter(BaseModelAdapter):
    """Deterministic adapter that produces structured output from packet data."""

    adapter_name = "mock"

    def reason(self, packet: Dict[str, Any]) -> ReasoningResult:
        request_id = packet.get("request_id", "mock-req-001")
        question = packet.get("question", "No question provided")
        evidence = packet.get("evidence", [])
        topic = packet.get("topic", "general")
        ttl_str = ttl_from_packet(packet)
        ttl_sec = compute_claim_ttl_seconds(packet)

        claim_hash = hashlib.sha256(question.encode()).hexdigest()[:8]

        claims = [
            CandidateClaim(
                claim_id=f"MOCK-C-{claim_hash}-1",
                text=f"Based on the evidence, the answer to '{question[:50]}' is affirmative",
                claim_type="inference",
                confidence=0.82,
                citations=[str(e) for e in evidence[:2]] if evidence else [],
                ttl_seconds=ttl_sec,
            ),
            CandidateClaim(
                claim_id=f"MOCK-C-{claim_hash}-2",
                text=f"Topic '{topic}' is within expected operational parameters",
                claim_type="fact",
                confidence=0.90,
                citations=[str(e) for e in evidence[:1]] if evidence else [],
                ttl_seconds=ttl_sec,
            ),
        ]

        reasoning = [
            ReasoningStep(
                step_id=f"MOCK-S-{claim_hash}-1",
                kind="observation",
                text=f"Reviewing evidence for topic '{topic}'",
                evidence_refs=[str(e) for e in evidence[:2]] if evidence else [],
            ),
            ReasoningStep(
                step_id=f"MOCK-S-{claim_hash}-2",
                kind="inference",
                text=f"Drawing conclusion for question: {question[:80]}",
            ),
        ]

        return ReasoningResult(
            request_id=request_id,
            adapter_name=self.adapter_name,
            claims=claims,
            reasoning=reasoning,
            confidence=0.85,
            citations=[str(e) for e in evidence] if evidence else [],
            contradictions=[],
            model_meta=ModelMeta(
                provider="local",
                model="mock-deterministic-v1",
                adapter_name=self.adapter_name,
                version="1.0.0",
                runtime="in-process",
            ),
            ttl=ttl_str,
        )
