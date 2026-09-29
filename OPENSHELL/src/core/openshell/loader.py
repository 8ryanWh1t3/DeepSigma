"""YAML/JSON loaders for AgentMissionContract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from .models import AgentMissionContract, EndpointPermission, L7Rule


def contract_from_dict(data: Dict[str, Any]) -> AgentMissionContract:
    endpoints = []
    for raw in data.get("endpoints", []) or []:
        rules = [
            L7Rule(
                method=str(r.get("method", "")),
                path=str(r.get("path", "")),
                allow=bool(r.get("allow", True)),
            )
            for r in raw.get("rules", []) or []
        ]
        endpoints.append(
            EndpointPermission(
                name=str(raw.get("name", "")),
                host=str(raw.get("host", "")),
                port=int(raw.get("port", 443)),
                protocol=raw.get("protocol", "rest"),
                enforcement=raw.get("enforcement", "enforce"),
                tls=raw.get("tls", "terminate"),
                access=raw.get("access", "read-only"),
                binaries=list(raw.get("binaries", []) or []),
                rules=rules,
                credential_bound=bool(raw.get("credential_bound", False)),
                description=str(raw.get("description", "")),
            )
        )

    known = {
        "contract_id", "episode_id", "mission", "objective", "agent_id", "actor_id",
        "command", "authority_scope", "role", "blast_radius_tier", "read_only_paths",
        "read_write_paths", "endpoints", "include_workdir", "process_user", "process_group",
        "assumptions", "evidence_refs", "kill_conditions", "expected_outputs",
        "human_approval_required", "sandbox_image", "metadata",
    }
    contract = AgentMissionContract(
        contract_id=str(data.get("contract_id", "")),
        episode_id=str(data.get("episode_id", "")),
        mission=str(data.get("mission", "")),
        objective=str(data.get("objective", "")),
        agent_id=str(data.get("agent_id", "")),
        actor_id=str(data.get("actor_id", "")),
        command=list(data.get("command", []) or []),
        authority_scope=str(data.get("authority_scope", "")),
        role=str(data.get("role", "agent")),
        blast_radius_tier=str(data.get("blast_radius_tier", "small")),
        read_only_paths=list(data.get("read_only_paths", []) or []),
        read_write_paths=list(data.get("read_write_paths", []) or []),
        endpoints=endpoints,
        include_workdir=bool(data.get("include_workdir", True)),
        process_user=data.get("process_user"),
        process_group=data.get("process_group"),
        assumptions=list(data.get("assumptions", []) or []),
        evidence_refs=list(data.get("evidence_refs", []) or []),
        kill_conditions=list(data.get("kill_conditions", []) or []),
        expected_outputs=list(data.get("expected_outputs", []) or []),
        human_approval_required=bool(data.get("human_approval_required", False)),
        sandbox_image=data.get("sandbox_image"),
        metadata=dict(data.get("metadata", {}) or {}),
    )
    # Preserve unknown top-level fields without silently discarding source intent.
    extras = {k: v for k, v in data.items() if k not in known}
    if extras:
        contract.metadata.setdefault("source_extensions", {}).update(extras)
    contract.validate()
    return contract


def load_contract(path: str | Path) -> AgentMissionContract:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("mission contract must be a YAML/JSON mapping")
    return contract_from_dict(data)


__all__ = ["contract_from_dict", "load_contract"]
