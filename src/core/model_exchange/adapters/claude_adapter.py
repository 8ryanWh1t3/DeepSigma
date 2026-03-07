"""Claude adapter — governed integration with Anthropic API models.

Configuration via environment variables:
  DEEPSIGMA_CLAUDE_API_KEY   API key (required for live mode)
  DEEPSIGMA_CLAUDE_MODEL     model name (default: claude-sonnet-4-20250514)
  DEEPSIGMA_CLAUDE_MODE      mock | live (default: mock)

In mock mode, returns deterministic output without any network calls.
In live mode, calls the Anthropic Messages API and parses the response.
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


class ClaudeAdapter(BaseModelAdapter):
    """Adapter for Anthropic Claude models."""

    adapter_name = "claude"

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._mode = mode or os.environ.get("DEEPSIGMA_CLAUDE_MODE", "mock")
        self._api_key = api_key or os.environ.get("DEEPSIGMA_CLAUDE_API_KEY", "")
        self._model = model or os.environ.get(
            "DEEPSIGMA_CLAUDE_MODEL", "claude-sonnet-4-20250514"
        )

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
        request_id = packet.get("request_id", "claude-req-001")
        question = packet.get("question", "No question provided")
        evidence = packet.get("evidence", [])
        topic = packet.get("topic", "general")
        ttl_str = ttl_from_packet(packet)
        ttl_sec = compute_claim_ttl_seconds(packet)

        h = hashlib.sha256(question.encode()).hexdigest()[:8]

        claims = [
            CandidateClaim(
                claim_id=f"CLD-C-{h}-1",
                text=f"Claude assessment: '{question[:50]}' — evidence supports conclusion",
                claim_type="inference",
                confidence=0.87,
                citations=[str(e) for e in evidence[:2]] if evidence else [],
                ttl_seconds=ttl_sec,
            ),
            CandidateClaim(
                claim_id=f"CLD-C-{h}-2",
                text=f"Risk assessment for '{topic}': within acceptable bounds",
                claim_type="risk",
                confidence=0.91,
                citations=[str(e) for e in evidence[:1]] if evidence else [],
                ttl_seconds=ttl_sec,
            ),
        ]

        reasoning = [
            ReasoningStep(
                step_id=f"CLD-S-{h}-1",
                kind="observation",
                text=f"Analyzing {len(evidence)} evidence items for '{topic}'",
                evidence_refs=[str(e) for e in evidence[:2]] if evidence else [],
            ),
            ReasoningStep(
                step_id=f"CLD-S-{h}-2",
                kind="comparison",
                text="Comparing against known operational baselines",
            ),
            ReasoningStep(
                step_id=f"CLD-S-{h}-3",
                kind="inference",
                text=f"Synthesising answer for: {question[:80]}",
            ),
        ]

        return ReasoningResult(
            request_id=request_id,
            adapter_name=self.adapter_name,
            claims=claims,
            reasoning=reasoning,
            confidence=0.88,
            citations=[str(e) for e in evidence] if evidence else [],
            contradictions=[],
            model_meta=self._meta(),
            ttl=ttl_str,
        )

    # -- live mode --

    def _reason_live(self, packet: Dict[str, Any]) -> ReasoningResult:
        request_id = packet.get("request_id", "claude-live-001")
        if not self._api_key:
            return self._error_result(
                request_id, "DEEPSIGMA_CLAUDE_API_KEY not configured"
            )
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError:
            return self._error_result(
                request_id,
                "anthropic package not installed — pip install anthropic",
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
            client = anthropic.Anthropic(api_key=self._api_key)
            message = client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = message.content[0].text if message.content else ""
        except Exception as exc:
            return self._error_result(request_id, f"Anthropic API error: {exc}")

        return self._parse_response(request_id, content, packet)

    def _parse_response(
        self, request_id: str, content: str, packet: Dict[str, Any]
    ) -> ReasoningResult:
        try:
            data = json.loads(content)
            claims = [
                CandidateClaim(
                    claim_id=f"CLD-LIVE-{i}",
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
                        claim_id=f"CLD-RAW-{request_id}",
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
                warnings=["Could not parse structured JSON from Claude response"],
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
            provider="anthropic",
            model=self._model,
            adapter_name=self.adapter_name,
            version=None,
            runtime="api" if self._mode == "live" else "mock",
        )
