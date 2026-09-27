from __future__ import annotations

import re
from dataclasses import replace

from ..models import (
    Assumption,
    Claim,
    Confidence,
    Evidence,
    Event,
    Intent,
    Modality,
    ProvenanceRef,
    SemanticPacket,
    Transcript,
)

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_PROBABLE = re.compile(r"\b(probably|likely|appears|seems|should be able to)\b", re.I)
_POSSIBLE = re.compile(r"\b(maybe|possibly|could|might|may)\b", re.I)
_REQUIRED = re.compile(r"\b(must|shall|required to|need to)\b", re.I)
_PROHIBITED = re.compile(r"\b(must not|shall not|prohibited|cannot)\b", re.I)
_NEGATION = re.compile(r"\b(no|not|never|cannot|can't|won't|doesn't|isn't|aren't)\b", re.I)
_ASSUMPTION = re.compile(r"\b(assuming|assume|if|provided that|as long as)\b", re.I)
_CONCERN = re.compile(r"\b(concern|concerned|risk|gap|problem|issue|warning)\b", re.I)
_INTENT = re.compile(r"\b(intend|goal|objective|want to|need to|plan to|trying to)\b", re.I)


class ConservativeSemanticExtractor:
    """Precision-first offline extractor.

    It deliberately avoids pretending to resolve deep entities or relationships. Every
    meaningful utterance becomes source-linked evidence plus a candidate claim. Stronger
    local NLP/LLM extractors can replace this adapter without changing downstream models.
    """

    def extract(self, transcript: Transcript) -> SemanticPacket:
        packet = SemanticPacket(transcript=transcript)
        segments = transcript.segments or ()

        if segments:
            utterances = list(segments)
        else:
            utterances = []
            for sentence in filter(None, (s.strip() for s in _SENTENCE_RE.split(transcript.text))):
                from ..models import TranscriptSegment

                utterances.append(TranscriptSegment(text=sentence))

        for idx, segment in enumerate(utterances):
            provenance = ProvenanceRef(
                source_id=transcript.source_id,
                source_type="voice-transcript",
                speaker_id=segment.speaker_id,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                observed_at=transcript.created_at,
                transform_chain=("transcript", "conservative-semantic-extractor:v0.1.0"),
            )
            evidence = Evidence(
                text=segment.text,
                provenance=provenance,
                confidence=segment.confidence,
            )
            packet.evidence.append(evidence)

            modality, semantic_conf = self._modality(segment.text, segment.confidence)
            claim = Claim(
                text=segment.text,
                confidence=semantic_conf,
                modality=modality,
                negated=bool(_NEGATION.search(segment.text)),
                evidence_ids=(evidence.id,),
                subject=segment.speaker_id,
            )
            packet.claims.append(claim)

            if _ASSUMPTION.search(segment.text):
                packet.assumptions.append(
                    Assumption(
                        statement=segment.text,
                        confidence=Confidence(
                            max(0.35, semantic_conf.value - 0.10),
                            "assumption cue detected in utterance",
                        ),
                        evidence_ids=(evidence.id,),
                    )
                )

            if _CONCERN.search(segment.text):
                packet.events.append(
                    Event(
                        description=f"Concern/risk signal raised: {segment.text}",
                        confidence=Confidence(
                            semantic_conf.value,
                            "explicit concern/risk language detected",
                        ),
                        evidence_ids=(evidence.id,),
                        event_type="risk_signal",
                    )
                )

            if _INTENT.search(segment.text):
                packet.intents.append(
                    Intent(
                        goal=segment.text,
                        confidence=Confidence(
                            semantic_conf.value,
                            "intent/goal language detected",
                        ),
                        actor_id=segment.speaker_id,
                        evidence_ids=(evidence.id,),
                    )
                )

        packet.metadata.update(
            {
                "extractor": "ConservativeSemanticExtractor",
                "extractor_version": "0.1.0",
                "semantic_policy": "precision-first; no automatic authority promotion",
                "utterance_count": len(utterances),
            }
        )
        return packet

    @staticmethod
    def _modality(text: str, source_confidence: Confidence) -> tuple[Modality, Confidence]:
        value = source_confidence.value
        rationale = ["source confidence inherited"]

        if _PROHIBITED.search(text):
            return Modality.PROHIBITED, Confidence(min(value, 0.95), "prohibition cue detected")
        if _REQUIRED.search(text):
            return Modality.REQUIRED, Confidence(min(value, 0.95), "requirement cue detected")
        if text.strip().endswith("?"):
            return Modality.QUESTION, Confidence(min(value, 0.90), "question punctuation detected")
        if _POSSIBLE.search(text):
            return Modality.POSSIBLE, Confidence(min(value, 0.55), "possibility cue detected")
        if _PROBABLE.search(text):
            return Modality.PROBABLE, Confidence(min(value, 0.70), "probability cue detected")

        rationale.append("no uncertainty cue detected")
        return Modality.ASSERTED, Confidence(min(value, 0.85), "; ".join(rationale))


class PassthroughPostProcessor:
    def process(self, packet: SemanticPacket) -> SemanticPacket:
        return replace(packet)
