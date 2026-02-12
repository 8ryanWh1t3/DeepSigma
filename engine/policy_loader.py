"""Policy Pack loader with hash verification.

Closes #10 — verifies policyPackHash at load time.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PolicyPackIntegrityError(Exception):
    """Raised when a policy pack's hash does not match its declared policyPackHash."""


def _compute_hash(pack: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of pack content, excluding the policyPackHash field."""
    content = {k: v for k, v in pack.items() if k != "policyPackHash"}
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_policy_pack(
    path: str,
    verify_hash: bool | None = None,
) -> Dict[str, Any]:
    """Load a policy pack JSON file and optionally verify its integrity hash.

    Args:
        path: Path to the policy pack JSON file.
        verify_hash: If True, verify the policyPackHash field against computed hash.
            If None (default), checks DEEPSIGMA_NO_VERIFY_HASH env var.
            Set to False to skip verification entirely.

    Returns:
        Parsed policy pack dict.

    Raises:
        PolicyPackIntegrityError: If hash verification fails and verify_hash is True.
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    p = Path(path)
    pack = json.loads(p.read_text(encoding="utf-8"))

    # Determine whether to verify
    if verify_hash is None:
        verify_hash = os.environ.get("DEEPSIGMA_NO_VERIFY_HASH", "").lower() not in (
            "1", "true", "yes"
        )

    if not verify_hash:
        logger.debug("Hash verification skipped for %s", path)
        return pack

    declared_hash = pack.get("policyPackHash")

    if declared_hash is None:
        logger.warning(
            "Policy pack %s has no policyPackHash field — loaded without verification",
            path,
        )
        return pack

    computed = _compute_hash(pack)
    if computed != declared_hash:
        raise PolicyPackIntegrityError(
            f"Policy pack integrity check failed for {path}: "
            f"declared hash={declared_hash!r}, computed hash={computed!r}"
        )

    logger.debug("Policy pack %s hash verified: %s", path, computed[:12])
    return pack


def get_rules(pack: Dict[str, Any], decision_type: str) -> Dict[str, Any]:
    """Get rules for a specific decision type from a policy pack."""
    return pack.get("rules", {}).get(decision_type, {})
