"""Declarative cascade rules — cross-domain event propagation.

Each rule defines: when a source domain emits an event with a given subtype,
the cascade engine invokes a target handler in the target domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class CascadeRule:
    """A single cross-domain cascade rule."""

    rule_id: str
    name: str
    source_domain: str
    source_subtype: str
    target_domain: str
    target_function_id: str
    description: str = ""
    severity_filter: Optional[str] = None  # Only trigger if severity matches


# ── Core cascade rules ───────────────────────────────────────────

RULES: List[CascadeRule] = [
    # IntelOps -> FranOps
    CascadeRule(
        rule_id="CASCADE-R01",
        name="contradiction_triggers_review",
        source_domain="intelops",
        source_subtype="claim_contradiction",
        target_domain="franops",
        target_function_id="FRAN-F03",
        description="Claim contradiction triggers canon enforcement check.",
    ),
    CascadeRule(
        rule_id="CASCADE-R02",
        name="supersede_triggers_canon_update",
        source_domain="intelops",
        source_subtype="claim_superseded",
        target_domain="franops",
        target_function_id="FRAN-F09",
        description="Claim supersede triggers canon supersede workflow.",
    ),

    # FranOps -> ReOps
    CascadeRule(
        rule_id="CASCADE-R03",
        name="retcon_flags_episodes",
        source_domain="franops",
        source_subtype="retcon_executed",
        target_domain="reflectionops",
        target_function_id="RE-F01",
        description="Retcon execution flags affected episodes for review.",
    ),

    # FranOps -> IntelOps
    CascadeRule(
        rule_id="CASCADE-R04",
        name="retcon_invalidates_claims",
        source_domain="franops",
        source_subtype="retcon_cascade",
        target_domain="intelops",
        target_function_id="INTEL-F12",
        description="Retcon cascade triggers confidence recalc on dependent claims.",
    ),

    # ReOps -> IntelOps + FranOps
    CascadeRule(
        rule_id="CASCADE-R05",
        name="freeze_stales_claims",
        source_domain="reflectionops",
        source_subtype="episodes_frozen",
        target_domain="intelops",
        target_function_id="INTEL-F11",
        description="Episode freeze triggers half-life check on related claims.",
    ),

    # ReOps -> All (kill-switch)
    CascadeRule(
        rule_id="CASCADE-R06",
        name="killswitch_freezes_all",
        source_domain="reflectionops",
        source_subtype="killswitch_activated",
        target_domain="reflectionops",
        target_function_id="RE-F06",
        description="Kill-switch propagates to ensure all domains freeze.",
        severity_filter="red",
    ),

    # Any -> ReOps (drift red threshold)
    CascadeRule(
        rule_id="CASCADE-R07",
        name="red_drift_triggers_severity",
        source_domain="*",
        source_subtype="*",
        target_domain="reflectionops",
        target_function_id="RE-F08",
        description="Any red-severity drift signal triggers centralized severity scoring.",
        severity_filter="red",
    ),
]


def get_rules_for_event(
    source_domain: str, source_subtype: str, severity: str = "",
) -> List[CascadeRule]:
    """Find cascade rules matching a given event."""
    matches: List[CascadeRule] = []
    for rule in RULES:
        domain_match = rule.source_domain in ("*", source_domain)
        subtype_match = rule.source_subtype in ("*", source_subtype)
        severity_match = (
            rule.severity_filter is None or rule.severity_filter == severity
        )
        if domain_match and subtype_match and severity_match:
            matches.append(rule)
    return matches
