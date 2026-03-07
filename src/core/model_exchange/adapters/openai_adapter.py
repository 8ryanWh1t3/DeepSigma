"""OpenAI adapter — governed integration with OpenAI API models.

Configuration via environment variables:
  DEEPSIGMA_OPENAI_API_KEY   API key (required for live mode)
  DEEPSIGMA_OPENAI_MODEL     model name (default: gpt-4o)
  DEEPSIGMA_OPENAI_MODE      mock | live (default: mock)

In mock mode, returns deterministic output without any network calls.
In live mode, calls the OpenAI Chat Completions API and parses the response.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional

from ..base_adapter import BaseModelAdapter
from ..models import (
    CandidateClaim,
    ModelMeta,
    ReasoningResult,
    ReasoningStep,
)
from ..ttl import compute_claim_ttl_seconds, ttl_from_packet


class OpenAIAdapter(BaseModelAdapter):
    """Adapter for OpenAI API models (GPT-4o, etc.)."""

    adapter_name = "openai"

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._mode = mode or os.environ.get("DEEPSIGMA_OPENAI_MODE", "mock")
        self._api_key = api_key or os.environ.get("DEEPSIGMA_OPENAI_API_KEY", "")
        self._model = model or os.environ.get("DEEPSIGMA_OPENAI_MODEL", "gpt-4o")

    def reason(self, packet: Dict[str, Any]) -> ReasoningResult:
        if self._mode == "live":
            return self._reason_live(packet)
        return self._reason_mock(packet)

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["mode"] = self._mode
        base["model"] = self._model
        base["api_key_configured"] = bool(self._api_key)
        return base

    # -- mock mode --

    def _reason_mock(self, packet: Dict[str, Any]) -> ReasoningResult:
        request_id = packet.get("request_id", "openai-req-001")
        question = packet.get("question", "No question provided")
        evidence = packet.get("evidence", [])
        topic = packet.get("topic", "general")
        ttl_str = ttl_from_packet(packet)
        ttl_sec = compute_claim_ttl_seconds(packet)

        h = hashlib.sha256(question.encode()).hexdigest()[:8]

        claims = [
            CandidateClaim(
                claim_id=f"OAI-C-{h}-1",
                text=f"OpenAI analysis: '{question[:50]}' indicates nominal state",
                claim_type="inference",
                confidence=0.85,
                citations=[str(e) for e in evidence[:2]] if evidence else [],
                ttl_seconds=ttl_sec,
            ),
        ]

        reasoning = [
            ReasoningStep(
                step_id=f"OAI-S-{h}-1",
                kind="observation",
                text=f"Evaluating evidence for '{topic}'",
                evidence_refs=[str(e) for e in evidence[:2]] if evidence else [],
            ),
            ReasoningStep(
                step_id=f"OAI-S-{h}-2",
                kind="inference",
                text=f"Generating response for: {question[:80]}",
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
            model_meta=self._meta(),
            ttl=ttl_str,
        )

    # -- live mode --

    def _reason_live(self, packet: Dict[str, Any]) -> ReasoningResult:
        request_id = packet.get("request_id", "openai-live-001")
        if not self._api_key:
            return self._error_result(
                request_id, "DEEPSIGMA_OPENAI_API_KEY not configured"
            )
        try:
            import openai  # type: ignore[import-untyped]
        except ImportError:
            return self._error_result(
                request_id,
                "openai package not installed — pip install openai",
            )

        question = packet.get("question", "")
        evidence = packet.get("evidence", [])
        topic = packet.get("topic", "general")

        system_prompt = (
            "You are a reasoning engine for Deep Sigma. "
            "Provide structured claims with confidence scores. "
            "Return valid JSON with keys: claims (array of {text, claimType, confidence}), "
            "reasoning (array of {text, kind}), confidence (float)."
        )
        user_prompt = (
            f"Topic: {topic}\nQuestion: {question}\n"
            f"Evidence: {json.dumps(evidence)}"
        )

        try:
            client = openai.OpenAI(api_key=self._api_key)
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=2048,
            )
            content = response.choices[0].message.content or ""
        except Exception as exc:
            return self._error_result(request_id, f"OpenAI API error: {exc}")

        return self._parse_response(request_id, content, packet)

    def _parse_response(
        self, request_id: str, content: str, packet: Dict[str, Any]
    ) -> ReasoningResult:
        try:
            data = json.loads(content)
            claims = [
                CandidateClaim(
                    claim_id=f"OAI-LIVE-{i}",
                    text=c.get("text", ""),
                    claim_type=c.get("claimType", "inference"),
                    confidence=float(c.get("confidence", 0.5)),
                    citations=c.get("citations", []),
                )
                for i, c in enumerate(data.get("claims", []))
            ]
            return ReasoningResult(
                request_id=request_id,
                adapter_name=self.adapter_name,
                claims=claims,
                reasoning=[],
                confidence=float(data.get("confidence", 0.5)),
                citations=data.get("citations", []),
                contradictions=[],
                model_meta=self._meta(),
                raw_json=data,
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return ReasoningResult(
                request_id=request_id,
                adapter_name=self.adapter_name,
                claims=[
                    CandidateClaim(
                        claim_id=f"OAI-RAW-{request_id}",
                        text=content[:500] if content else "(empty)",
                        claim_type="inference",
                        confidence=0.3,
                    )
                ],
                reasoning=[],
                confidence=0.3,
                citations=[],
                contradictions=[],
                model_meta=self._meta(),
                raw_text=content,
                warnings=["Could not parse structured JSON from OpenAI response"],
            )

    def _error_result(self, request_id: str, message: str) -> ReasoningResult:
        return ReasoningResult(
            request_id=request_id,
            adapter_name=self.adapter_name,
            claims=[],
            reasoning=[],
            confidence=0.0,
            citations=[],
            contradictions=[],
            model_meta=self._meta(),
            warnings=[message],
        )

    def _meta(self) -> ModelMeta:
        return ModelMeta(
            provider="openai",
            model=self._model,
            adapter_name=self.adapter_name,
            version=None,
            runtime="api" if self._mode == "live" else "mock",
        )
