"""Artifact Builder — Primitive 3: Executable Artifacts.

Serializes compiled policies to inspectable JSON files on disk.
Supports write, load, and seal verification.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from .models import CompiledPolicy
from .seal_and_hash import compute_hash, verify_seal


def build_artifact(compiled: CompiledPolicy) -> dict:
    """Convert a CompiledPolicy to a serializable artifact dict.

    Returns:
        Dict with artifactId, sourceId, dlrRef, rules, reasoning,
        policyHash, and seal.
    """
    rules = [
        {
            "constraintId": r.constraint_id,
            "constraintType": r.constraint_type,
            "expression": r.expression,
            "parameters": r.parameters,
        }
        for r in compiled.rules
    ]

    reasoning = None
    if compiled.reasoning_requirements is not None:
        rr = compiled.reasoning_requirements
        reasoning = {
            "requirementId": rr.requirement_id,
            "requiresDlr": rr.requires_dlr,
            "minimumClaims": rr.minimum_claims,
            "requiredTruthTypes": rr.required_truth_types,
            "minimumConfidence": rr.minimum_confidence,
            "maxAssumptionAge": rr.max_assumption_age,
        }

    # Build the artifact body (everything except the seal)
    body = {
        "artifactId": compiled.artifact_id,
        "sourceId": compiled.source_id,
        "dlrRef": compiled.dlr_ref,
        "episodeId": compiled.episode_id,
        "policyPackId": compiled.policy_pack_id,
        "rules": rules,
        "reasoningRequirements": reasoning,
        "policyHash": compiled.policy_hash,
        "createdAt": compiled.created_at,
    }

    body_hash = compute_hash(body)
    body["seal"] = {
        "hash": body_hash,
        "sealedAt": compiled.created_at,
        "version": compiled.seal_version,
    }

    return body


def write_artifact(compiled: CompiledPolicy, output_dir: Path) -> Path:
    """Write a compiled policy artifact to disk as JSON.

    Returns:
        Path to the written artifact file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = build_artifact(compiled)
    path = output_dir / f"{compiled.artifact_id}.json"
    path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return path


def load_artifact(path: Path) -> dict:
    """Load an artifact from disk and verify its seal.

    Raises:
        ValueError: If the seal does not match.

    Returns:
        The artifact dict.
    """
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if not verify_artifact(artifact):
        raise ValueError(f"Artifact seal verification failed: {path}")
    return artifact


def verify_artifact(artifact: dict) -> bool:
    """Verify an artifact's seal without raising."""
    seal_block = artifact.get("seal", {})
    expected_hash = seal_block.get("hash", "")
    if not expected_hash:
        return False
    # Recompute hash over body (everything except the seal)
    body = {k: v for k, v in artifact.items() if k != "seal"}
    return verify_seal(body, expected_hash)
