from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .models import ContrastResult


@dataclass(frozen=True)
class CerpaHandoff:
    claim: str
    event: str
    review: dict[str, Any]
    patch: dict[str, Any]
    apply_status: str = "PENDING_AUTHORITY"
    authoritative: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def to_cerpa_handoff(
    result: ContrastResult,
    *,
    claim: str | None = None,
    proposed_patch: str | None = None,
) -> CerpaHandoff:
    """
    Convert contrast findings into a governed CERPA handoff.

    This function deliberately does not APPLY anything.
    Human / institutional authority must evaluate and authorize a patch.
    """
    top = [f.description for f in result.discriminating_factors[:5]]
    claim_text = claim or (
        f"Episode {result.current_episode_id} materially differs from "
        f"{result.prior_episode_id} in factors that may explain outcome divergence."
    )
    event = (
        f"Contrast generated with similarity={result.similarity:.3f} "
        f"and confidence={result.confidence:.3f}."
    )
    review = {
        "material_differences": list(result.material_differences),
        "discriminating_factors": top,
        "advisory_only": True,
    }
    patch = {
        "proposal": proposed_patch or "Review discriminating factors and determine whether governed knowledge requires change.",
        "status": "PROPOSED",
        "requires_authority": True,
    }
    return CerpaHandoff(
        claim=claim_text,
        event=event,
        review=review,
        patch=patch,
        apply_status="PENDING_AUTHORITY",
        authoritative=False,
    )
