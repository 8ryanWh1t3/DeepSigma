"""CERPA Agent Supervision Demo — AI governance scenario.

Demonstrates the CERPA adaptation loop as an AI supervision cycle:

    Claim:  "Agent must not emit restricted content"
    Event:  "Agent emitted restricted content"
    Review: policy violation detected
    Patch:  strengthen controls
    Apply:  updated governed state

Run:
    python -m src.core.examples.cerpa_agent_supervision_demo
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.cerpa.engine import cycle_to_dict, run_cerpa_cycle  # noqa: E402
from core.cerpa.models import Claim, Event  # noqa: E402


def run_agent_supervision_demo() -> dict:
    """Run the agent supervision CERPA demo and return the cycle dict."""

    claim = Claim(
        id="claim-agent-001",
        text="Agent must not emit restricted content in responses",
        domain="authorityops",
        source="governance-policy-001",
        timestamp="2026-03-01T08:00:00Z",
        assumptions=["Content filter is active", "Policy rules are current"],
        authority="compliance-officer",
        provenance=[{"type": "policy", "ref": "pol-content-001", "role": "governing"}],
    )

    event = Event(
        id="event-agent-001",
        text="Agent emitted restricted content in customer response",
        domain="authorityops",
        source="content-monitor",
        timestamp="2026-03-02T14:30:00Z",
        observed_state={"status": "violated", "content_type": "restricted"},
        metadata={
            "violation": True,
            "violation_detail": "Agent produced restricted content bypassing filter",
        },
    )

    cycle = run_cerpa_cycle(claim, event)
    result = cycle_to_dict(cycle)

    # Print labeled output
    print("=== CERPA Cycle: Agent Supervision ===")
    print()
    print(f"CLAIM    {claim.id}  {claim.text}")
    print(f"EVENT    {event.id}  {event.text}")
    print(f"REVIEW   {cycle.review.id}  verdict={cycle.review.verdict}  drift={cycle.review.drift_detected}")
    if cycle.patch:
        print(f"PATCH    {cycle.patch.id}  action={cycle.patch.action}  target={cycle.patch.target}")
    if cycle.apply_result:
        print(f"APPLY    {cycle.apply_result.id}  success={cycle.apply_result.success}")
    print()
    print(f"STATUS   {cycle.status}")
    print()
    print("--- Cycle JSON ---")
    print(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    run_agent_supervision_demo()
