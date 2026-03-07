"""CERPA Contract Delivery Demo — governance scenario.

Demonstrates the CERPA adaptation loop using a simple contract claim:

    Claim:  "Contractor shall deliver artifact X by date Y"
    Event:  "Artifact X not delivered by date Y"
    Review: mismatch detected
    Patch:  adjust plan / escalate
    Apply:  new active claim state

Run:
    python -m src.core.examples.cerpa_contract_demo
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


def run_contract_demo() -> dict:
    """Run the contract delivery CERPA demo and return the cycle dict."""

    claim = Claim(
        id="claim-contract-001",
        text="Contractor shall deliver artifact X by 2026-03-15",
        domain="actionops",
        source="contract-pm-001",
        timestamp="2026-03-01T09:00:00Z",
        assumptions=["Contractor has resources available", "No supply chain delays"],
        authority="contracting-officer",
        provenance=[{"type": "contract", "ref": "contract-2026-001", "role": "source"}],
    )

    event = Event(
        id="event-contract-001",
        text="Artifact X not delivered by 2026-03-15",
        domain="actionops",
        source="delivery-tracker",
        timestamp="2026-03-16T08:00:00Z",
        observed_state={"status": "failed", "artifact": "X", "deadline": "2026-03-15"},
        metadata={},
    )

    cycle = run_cerpa_cycle(claim, event)
    result = cycle_to_dict(cycle)

    # Print labeled output
    print("=== CERPA Cycle: Contract Delivery ===")
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
    run_contract_demo()
