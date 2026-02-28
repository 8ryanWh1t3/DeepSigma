"""Kill-switch — freeze all episodes, emit halt proof, log to audit.

Steps:
1. Freeze: all in-flight episodes -> FROZEN state
2. Halt proof: sealed bundle (who, why, when)
3. FEEDS event: drift_signal subtype killswitch, severity red
4. Resume: explicit authority check required
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .episode_state import EpisodeTracker


def activate_killswitch(
    tracker: EpisodeTracker,
    authorized_by: str,
    reason: str,
    audit_log: Optional[Any] = None,
) -> Dict[str, Any]:
    """Activate the kill-switch.

    Args:
        tracker: Episode state tracker.
        authorized_by: Who authorized the kill-switch.
        reason: Why the kill-switch was activated.
        audit_log: Optional AuditLog for recording the event.

    Returns:
        A halt proof dict.
    """
    frozen_ids = tracker.freeze_all()
    now = datetime.now(timezone.utc).isoformat()

    halt_proof = {
        "activatedAt": now,
        "authorizedBy": authorized_by,
        "reason": reason,
        "frozenEpisodes": frozen_ids,
        "frozenCount": len(frozen_ids),
    }

    # Seal the halt proof
    canonical = json.dumps(halt_proof, sort_keys=True, separators=(",", ":"))
    halt_proof["sealHash"] = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    # Record in audit log
    if audit_log is not None:
        from .audit_log import AuditEntry
        audit_log.append(AuditEntry(
            entry_type="killswitch_activated",
            detail=f"Kill-switch by {authorized_by}: {reason}",
            actor=authorized_by,
            metadata=halt_proof,
        ))

    return halt_proof
