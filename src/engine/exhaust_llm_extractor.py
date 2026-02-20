"""LLM-based extraction engine for the Exhaust Inbox.

Wraps the Anthropic Messages API to extract Truth/Reasoning/Memory
buckets from DecisionEpisodes. Falls back silently to empty buckets
if the API is unavailable, the key is missing, or the response is
unparseable — the rule-based extractor takes over transparently.

Install optional dep:
    pip install -e ".[exhaust-llm]"

Enable:
    export ANTHROPIC_API_KEY="sk-ant-..."
    export EXHAUST_USE_LLM="1"
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.server.models_exhaust import (
    DecisionEpisode,
    MemoryItem,
    ReasoningItem,
    TruthItem,
)

logger = logging.getLogger(__name__)

_MAX_PROMPT_CHARS = 6000

_SYSTEM_PROMPT = (
    "You are an institutional knowledge extractor for Σ OVERWATCH. "
    "Given an AI decision episode transcript, extract structured knowledge. "
    "Return ONLY valid JSON matching the schema below. "
    "No explanation, no markdown fences.\n\n"
    "Schema:\n"
    '{"truth": [{"claim": str, "confidence": float, "evidence": str}], '
    '"reasoning": [{"decision": str, "confidence": float, "rationale": str}], '
    '"memory": [{"entity": str, "entity_type": str, "relations": [str], "confidence": float}]}\n\n'
    "Rules:\n"
    "- confidence must be a float in [0.0, 1.0]\n"
    "- truth: verifiable factual claims (metrics, observed states, counts)\n"
    "- reasoning: decisions, recommendations, and their rationale\n"
    "- memory: entities, tools, models, and services mentioned\n"
    '- Return {"truth": [], "reasoning": [], "memory": []} if nothing found'
)


class LLMExtractor:
    """Extract truth/reasoning/memory via the Anthropic Messages API.

    Usage::

        extractor = LLMExtractor()
        buckets = extractor.extract(episode)
        # buckets = {"truth": [...], "reasoning": [...], "memory": [...]}
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 2048,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens

    def extract(self, episode: DecisionEpisode) -> Dict[str, List]:
        """Return ``{"truth": [...], "reasoning": [...], "memory": [...]}``.

        Falls back to empty buckets on any failure so the rule-based
        extractor can take over transparently.
        """
        try:
            prompt = self._build_prompt(episode)
            text = self._call_api(prompt)
            return self._parse_response(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM extraction failed, falling back to rule-based: %s", exc)
            return {"truth": [], "reasoning": [], "memory": []}

    # ── Internal methods ──────────────────────────────────────────

    def _build_prompt(self, episode: DecisionEpisode) -> str:
        """Summarize episode events as a readable transcript."""
        lines = [f"Episode: {episode.episode_id}  project={episode.project}"]
        for ev in episode.events:
            payload_str = json.dumps(ev.payload)[:400]
            lines.append(
                f"[{ev.event_type.value}] {ev.timestamp} "
                f"source={ev.source.value} payload={payload_str}"
            )
        transcript = "\n".join(lines)
        if len(transcript) > _MAX_PROMPT_CHARS:
            transcript = transcript[:_MAX_PROMPT_CHARS] + "\n...(truncated)"
        return f"Episode transcript:\n\n{transcript}\n\nExtract knowledge:"

    def _call_api(self, prompt: str) -> str:
        """Call Anthropic Messages API and return raw response text."""
        try:
            import anthropic  # optional dep
        except ImportError as exc:
            raise ImportError(
                "anthropic package required: pip install -e '.[exhaust-llm]'"
            ) from exc

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _parse_response(self, text: str) -> Dict[str, List]:
        """Parse and validate the LLM JSON response into bucket objects."""
        # Strip markdown fences if LLM ignored instructions
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            inner = lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:]
            stripped = "\n".join(inner)

        data: Dict[str, Any] = json.loads(stripped)

        def _clamp(v: Any, default: float = 0.5) -> float:
            try:
                return max(0.0, min(1.0, float(v)))
            except (TypeError, ValueError):
                return default

        truth: List[TruthItem] = []
        for item in data.get("truth", []):
            truth.append(TruthItem(
                claim=str(item.get("claim", "")),
                evidence=str(item.get("evidence", "llm_extracted")),
                confidence=_clamp(item.get("confidence")),
                truth_type="derived",
            ))

        reasoning: List[ReasoningItem] = []
        for item in data.get("reasoning", []):
            reasoning.append(ReasoningItem(
                decision=str(item.get("decision", "")),
                rationale=str(item.get("rationale", "")),
                confidence=_clamp(item.get("confidence")),
            ))

        memory: List[MemoryItem] = []
        for item in data.get("memory", []):
            memory.append(MemoryItem(
                entity=str(item.get("entity", "")),
                artifact_type=str(item.get("entity_type", "")),
                relation="mentioned_in",
                confidence=_clamp(item.get("confidence")),
            ))

        return {"truth": truth, "reasoning": reasoning, "memory": memory}
