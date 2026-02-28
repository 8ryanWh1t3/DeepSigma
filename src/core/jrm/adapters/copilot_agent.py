"""Copilot / agent JSONL adapter — parse agent log records into JRM events."""

from __future__ import annotations

import json
from typing import Any, Dict

from ..types import EventType, JRMEvent, Severity
from .base import AdapterBase

# Map agent record type to JRM EventType
_AGENT_TYPE_MAP: Dict[str, EventType] = {
    "prompt": EventType.AGENT_PROMPT,
    "tool_call": EventType.AGENT_TOOL_CALL,
    "response": EventType.AGENT_RESPONSE,
    "guardrail": EventType.AGENT_GUARDRAIL,
}


class CopilotAgentAdapter(AdapterBase):
    """Parse agent/copilot JSONL logs into normalized JRM events."""

    source_system = "copilot_agent"

    def parse_line(self, line: str, line_number: int = 0) -> JRMEvent | None:
        if not line.strip():
            return None

        try:
            record: Dict[str, Any] = json.loads(line)
        except (json.JSONDecodeError, ValueError) as exc:
            return self._make_malformed(line, line_number, str(exc))

        record_type = record.get("type", "generic")
        event_type = _AGENT_TYPE_MAP.get(record_type, EventType.GENERIC)

        # Determine severity from guardrail flags
        guardrail_flags = record.get("guardrail_flags", [])
        if guardrail_flags:
            severity = Severity.HIGH
        elif event_type == EventType.AGENT_GUARDRAIL:
            severity = Severity.MEDIUM
        else:
            severity = Severity.INFO

        # Actor is the agent, object is the target system/tool
        agent_id = record.get("agent_id", "agent")
        target = record.get("target", record.get("tool", "system"))
        if isinstance(target, dict):
            target_id = target.get("name", target.get("id", "system"))
        else:
            target_id = str(target)

        actor: Dict[str, Any] = {"type": "agent", "id": agent_id}
        obj: Dict[str, Any] = {"type": "tool", "id": target_id}

        # Confidence from record or default
        confidence = float(record.get("confidence", 0.5))

        raw_hash = self.hash_raw(line)
        timestamp = record.get("timestamp", "")

        # Build action
        if event_type == EventType.AGENT_TOOL_CALL:
            tool_calls = record.get("tool_calls", [])
            action = f"tool_call:{','.join(str(tc.get('name', '?')) for tc in tool_calls)}" if tool_calls else "tool_call"
        elif event_type == EventType.AGENT_GUARDRAIL:
            action = f"guardrail:{','.join(guardrail_flags)}" if guardrail_flags else "guardrail"
        elif event_type == EventType.AGENT_PROMPT:
            action = "prompt"
        elif event_type == EventType.AGENT_RESPONSE:
            action = "response"
        else:
            action = record_type

        # Assumptions from guardrail flags
        assumptions = [f"guardrail:{flag}" for flag in guardrail_flags]

        # Metadata: preserve prompt, tool_calls, response fragments
        metadata: Dict[str, Any] = {}
        if "prompt" in record:
            metadata["prompt"] = record["prompt"][:500]
        if "tool_calls" in record:
            metadata["tool_calls"] = record["tool_calls"]
        if "response" in record:
            metadata["response"] = record["response"][:500]
        if guardrail_flags:
            metadata["guardrail_flags"] = guardrail_flags
        if "model" in record:
            metadata["model"] = record["model"]

        return JRMEvent(
            event_id=self._generate_event_id("AGNT"),
            source_system=self.source_system,
            event_type=event_type,
            timestamp=timestamp,
            severity=severity,
            actor=actor,
            object=obj,
            action=action,
            confidence=confidence,
            evidence_hash=raw_hash,
            raw_pointer=f"inline:{raw_hash}",
            environment_id=self.default_environment_id,
            assumptions=assumptions,
            raw_bytes=line.encode("utf-8", errors="replace"),
            metadata=metadata,
        )
