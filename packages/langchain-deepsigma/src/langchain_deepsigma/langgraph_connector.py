"""Trace-to-canonical record mapper for graph execution traces.

Ingests graph execution traces (both ``astream_events`` v2 format and
run tree format) and maps them to canonical records for drift detection.

No runtime dependency on langchain or langgraph -- only parses trace JSON.

Usage::

    from langchain_deepsigma import LangGraphConnector

    connector = LangGraphConnector(graph_id="my-agent")
    records = connector.to_canonical(trace_events)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ._helpers import to_iso, uuid_from_hash

logger = logging.getLogger(__name__)

# ── Confidence mapping ───────────────────────────────────────────────────────

_RUN_TYPE_CONFIDENCE: Dict[str, float] = {
    "llm": 0.75,
    "tool": 0.90,
    "retriever": 0.80,
    "chain": 0.85,
}

_RECORD_TYPE_MAP: Dict[str, str] = {
    "llm": "Claim",
    "tool": "Event",
    "retriever": "Document",
    "chain": "Event",
}

_RUN_TYPE_TTL: Dict[str, int] = {
    "llm": 300_000,
    "tool": 600_000,
    "retriever": 600_000,
    "chain": 300_000,
}


class LangGraphConnector:
    """Graph trace connector.

    Accepts two trace formats:

    1. **astream_events v2** -- flat list of event dicts with ``event``,
       ``name``, ``run_id``, ``parent_ids``, ``metadata``, ``data`` keys.
    2. **Run tree** -- nested/flat Run dicts with ``run_type``,
       ``name``, ``start_time``, ``end_time``, ``inputs``, ``outputs``,
       ``parent_run_id``, ``trace_id``, ``extra.metadata`` keys.

    Parameters
    ----------
    graph_id : str
        Identifier for the graph (used in provenance URIs).
    source_instance : str
        Instance label (e.g. environment, deployment).
    """

    source_name = "langgraph"

    def __init__(
        self,
        graph_id: str = "default",
        source_instance: str = "",
    ) -> None:
        self._graph_id = graph_id
        self._source_instance = source_instance

    def list_records(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Not supported -- traces are pushed, not pulled."""
        raise NotImplementedError("Connector is push-based; use to_canonical().")

    def get_record(self, record_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Not supported -- traces are push-based."""
        raise NotImplementedError("Connector is push-based.")

    def to_canonical(self, trace_data: Any) -> List[Dict[str, Any]]:
        """Convert trace data to canonical records.

        Auto-detects the format:
        - List of dicts with ``"event"`` key -> astream_events v2
        - List of dicts with ``"run_type"`` key -> Run (flat)
        - Single dict with ``"run_type"`` and ``"child_runs"`` -> Run tree
        """
        if isinstance(trace_data, dict):
            if "run_type" in trace_data:
                runs = self._flatten_run_tree(trace_data)
                return self._runs_to_canonical(runs)
            if "events" in trace_data and isinstance(trace_data["events"], list):
                return self._events_to_canonical(trace_data["events"])
            logger.warning("Unrecognized trace dict format; treating as single run.")
            return self._runs_to_canonical([trace_data])

        if isinstance(trace_data, list) and trace_data:
            first = trace_data[0]
            if "event" in first:
                return self._events_to_canonical(trace_data)
            if "run_type" in first:
                return self._runs_to_canonical(trace_data)
            logger.warning("Unrecognized trace list format.")

        return []

    def to_agent_session_decisions(
        self, trace_data: Any,
    ) -> List[Dict[str, Any]]:
        """Convert trace data to AgentSession-compatible decision dicts.

        Each canonical record becomes a simplified decision dict that can
        be passed directly to ``AgentSession.log_decision()``.
        """
        records = self.to_canonical(trace_data)
        decisions = []
        for rec in records:
            content = rec.get("content", {})
            decisions.append({
                "action": content.get("run_type", "unknown"),
                "reason": f"Graph node: {content.get('node_name', 'unknown')}",
                "actor": {"type": "agent", "id": self._graph_id},
                "confidence": rec.get("confidence", {}).get("score"),
            })
        return decisions

    # ── astream_events v2 -> canonical ───────────────────────────────

    def _events_to_canonical(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        starts: Dict[str, Dict[str, Any]] = {}

        for ev in events:
            event_type = ev.get("event", "")
            run_id = ev.get("run_id", "")
            name = ev.get("name", "")
            metadata = ev.get("metadata", {})
            data = ev.get("data", {})

            if "_stream" in event_type:
                continue

            if event_type.endswith("_start"):
                starts[run_id] = ev
                continue

            if not event_type.endswith("_end"):
                continue

            start_ev = starts.pop(run_id, None)
            run_type = self._event_type_to_run_type(event_type)
            node_name = metadata.get("langgraph_node", name)
            step = metadata.get("langgraph_step")
            triggers = metadata.get("langgraph_triggers", [])

            input_data = start_ev.get("data", {}).get("input") if start_ev else None
            output_data = data.get("output")

            record = self._build_canonical_record(
                run_id=run_id,
                node_name=node_name,
                run_type=run_type,
                step=step,
                triggers=triggers,
                input_data=input_data,
                output_data=output_data,
                metadata=metadata,
            )
            records.append(record)

        return records

    @staticmethod
    def _event_type_to_run_type(event_type: str) -> str:
        if "chat_model" in event_type or "llm" in event_type:
            return "llm"
        if "tool" in event_type:
            return "tool"
        if "retriever" in event_type:
            return "retriever"
        return "chain"

    # ── Run -> canonical ─────────────────────────────────────────────

    def _runs_to_canonical(self, runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []

        for run in runs:
            run_type = run.get("run_type", "chain")
            name = run.get("name", "")
            run_id = run.get("id", "")
            metadata = run.get("extra", {}).get("metadata", {})
            node_name = metadata.get("langgraph_node", name)
            step = metadata.get("langgraph_step")
            triggers = metadata.get("langgraph_triggers", [])

            start_time = run.get("start_time", "")
            end_time = run.get("end_time", "")
            duration_ms = self._compute_duration_ms(start_time, end_time)

            record = self._build_canonical_record(
                run_id=str(run_id),
                node_name=node_name,
                run_type=run_type,
                step=step,
                triggers=triggers,
                input_data=run.get("inputs"),
                output_data=run.get("outputs"),
                metadata=metadata,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                status=run.get("status"),
                error=run.get("error"),
                trace_id=run.get("trace_id", ""),
                parent_run_id=run.get("parent_run_id", ""),
            )
            records.append(record)

        return records

    def _flatten_run_tree(self, root: Dict[str, Any]) -> List[Dict[str, Any]]:
        runs: List[Dict[str, Any]] = []
        stack = [root]
        while stack:
            run = stack.pop()
            flat = {k: v for k, v in run.items() if k != "child_runs"}
            runs.append(flat)
            for child in run.get("child_runs", []):
                stack.append(child)
        return runs

    # ── Shared helpers ───────────────────────────────────────────────

    def _build_canonical_record(
        self,
        *,
        run_id: str,
        node_name: str,
        run_type: str,
        step: Optional[int],
        triggers: List[str],
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        start_time: str = "",
        end_time: str = "",
        duration_ms: Optional[float] = None,
        status: Optional[str] = None,
        error: Optional[str] = None,
        trace_id: str = "",
        parent_run_id: str = "",
    ) -> Dict[str, Any]:
        record_id = uuid_from_hash("lg", f"{self._graph_id}:{run_id}")
        confidence = _RUN_TYPE_CONFIDENCE.get(run_type, 0.85)
        record_type = _RECORD_TYPE_MAP.get(run_type, "Event")
        ttl = _RUN_TYPE_TTL.get(run_type, 300_000)

        prov_uri = f"langgraph://{self._graph_id}/{node_name}"
        if step is not None:
            prov_uri += f"?step={step}"

        links = []
        for trigger in triggers:
            source_node = trigger.replace("start:", "__start__") if trigger.startswith("start:") else trigger
            links.append({
                "rel": "derived_from",
                "target": uuid_from_hash("lg", f"{self._graph_id}:{source_node}"),
            })

        content: Dict[str, Any] = {
            "node_name": node_name,
            "run_type": run_type,
        }
        if step is not None:
            content["step"] = step
        if input_data is not None:
            content["input"] = input_data
        if output_data is not None:
            content["output"] = output_data
        if duration_ms is not None:
            content["duration_ms"] = round(duration_ms, 1)
        if status:
            content["status"] = status
        if error:
            content["error"] = error

        tags = ["langgraph", f"node:{node_name}", f"type:{run_type}"]
        if trace_id:
            tags.append(f"trace:{trace_id}")

        observed_at = to_iso(start_time) if start_time else ""
        created_at = to_iso(end_time) if end_time else observed_at or datetime.now(timezone.utc).isoformat()

        return {
            "record_id": record_id,
            "record_type": record_type,
            "created_at": created_at,
            "observed_at": observed_at,
            "source": {
                "system": "langgraph",
                "actor": {"id": node_name, "type": "agent"},
            },
            "provenance": [
                {
                    "type": "source",
                    "ref": prov_uri,
                    "method": "trace_ingestion",
                }
            ],
            "confidence": {
                "score": confidence,
                "explanation": f"{run_type} execution with {'known' if status == 'success' else 'uncertain'} outcome",
            },
            "ttl": ttl,
            "content": content,
            "labels": {"tags": tags},
            "links": links,
        }

    @staticmethod
    def _compute_duration_ms(start_time: str, end_time: str) -> Optional[float]:
        if not start_time or not end_time:
            return None
        try:
            s = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            e = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            return (e - s).total_seconds() * 1000
        except (ValueError, TypeError):
            return None
