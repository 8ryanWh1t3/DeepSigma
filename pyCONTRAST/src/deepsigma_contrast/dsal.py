from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import ContrastResult, Episode


def episode_to_dko(episode: Episode) -> dict[str, Any]:
    payload = {
        "dkoType": "DecisionEpisode",
        "identity": {"id": episode.id, "version": episode.version},
        "meaning": {
            "title": episode.title,
            "claim": episode.claim,
            "decision": episode.decision,
            "rationale": episode.rationale,
        },
        "assumptions": [
            {
                "id": a.id,
                "statement": a.statement,
                "confidence": a.confidence,
                "status": a.status,
                "expiresAt": a.expires_at,
                "evidenceIds": list(a.evidence_ids),
            }
            for a in episode.assumptions
        ],
        "outcome": (
            {
                "status": episode.outcome.status,
                "summary": episode.outcome.summary,
                "metrics": dict(episode.outcome.metrics),
            }
            if episode.outcome
            else None
        ),
        "evidence": [
            {
                "id": e.id,
                "uri": e.uri,
                "weight": e.weight,
                "supports": e.supports,
            }
            for e in episode.evidence
        ],
        "context": {
            "tags": sorted(episode.tags),
            "entities": list(episode.entities),
            "metadata": dict(episode.metadata),
        },
        "governance": {
            "authority": "EXTERNAL",
            "advisory": True,
        },
    }
    payload["integrity"] = {"sha256": _hash(payload)}
    return payload


def contrast_to_dsal(result: ContrastResult) -> dict[str, Any]:
    payload = {
        "type": "ContrastLearningRecord",
        "currentEpisode": result.current_episode_id,
        "priorEpisode": result.prior_episode_id,
        "scores": {
            "similarity": result.similarity,
            "structuralSimilarity": result.structural_similarity,
            "lexicalSimilarity": result.lexical_similarity,
            "confidence": result.confidence,
        },
        "materialDifferences": list(result.material_differences),
        "discriminatingFactors": [
            {
                "key": x.key,
                "description": x.description,
                "weight": x.weight,
                "evidenceIds": list(x.evidence_ids),
            }
            for x in result.discriminating_factors
        ],
        "governance": {
            "advisoryOnly": True,
            "authorityRequiredForPatch": True,
            "applyPermitted": False,
        },
    }
    payload["integrity"] = {"sha256": _hash(payload)}
    return payload


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
