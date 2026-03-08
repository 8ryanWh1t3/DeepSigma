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

    # ── AuthorityOps cascade rules ──────────────────────────────

    # ReOps -> AuthorityOps
    CascadeRule(
        rule_id="CASCADE-R08",
        name="sealed_episode_triggers_authority",
        source_domain="reflectionops",
        source_subtype="episode_sealed",
        target_domain="authorityops",
        target_function_id="AUTH-F01",
        description="Sealed episode triggers authority evaluation for pending actions.",
    ),

    # AuthorityOps -> FranOps
    CascadeRule(
        rule_id="CASCADE-R09",
        name="authority_block_triggers_enforce",
        source_domain="authorityops",
        source_subtype="authority_block",
        target_domain="franops",
        target_function_id="FRAN-F03",
        description="Authority block triggers canon enforcement review.",
    ),

    # AuthorityOps -> ReOps
    CascadeRule(
        rule_id="CASCADE-R10",
        name="authority_escalation_triggers_episode",
        source_domain="authorityops",
        source_subtype="authority_escalate",
        target_domain="reflectionops",
        target_function_id="RE-F01",
        description="Authority escalation creates a new review episode.",
    ),

    # IntelOps -> AuthorityOps
    CascadeRule(
        rule_id="CASCADE-R11",
        name="authority_mismatch_triggers_delegation",
        source_domain="intelops",
        source_subtype="authority_mismatch",
        target_domain="authorityops",
        target_function_id="AUTH-F12",
        description="Authority mismatch in IntelOps triggers delegation chain validation.",
    ),

    # AuthorityOps -> IntelOps
    CascadeRule(
        rule_id="CASCADE-R12",
        name="stale_assumptions_trigger_recalc",
        source_domain="authorityops",
        source_subtype="assumptions_stale",
        target_domain="intelops",
        target_function_id="INTEL-F12",
        description="Stale assumptions in authority check trigger confidence recalculation.",
    ),

    # AuthorityOps kill-switch passthrough
    CascadeRule(
        rule_id="CASCADE-R13",
        name="killswitch_blocks_authority",
        source_domain="authorityops",
        source_subtype="killswitch_active",
        target_domain="reflectionops",
        target_function_id="RE-F06",
        description="Kill-switch active in authority check propagates to ReOps freeze.",
        severity_filter="red",
    ),

    # ── ActionOps cascade rules ──────────────────────────────────

    # AuthorityOps -> ActionOps
    CascadeRule(
        rule_id="CASCADE-R14",
        name="authority_approval_activates_commitment",
        source_domain="authorityops",
        source_subtype="authority_approved",
        target_domain="actionops",
        target_function_id="ACTION-F01",
        description="Authority approval triggers commitment registration.",
    ),

    # ActionOps -> ReflectionOps
    CascadeRule(
        rule_id="CASCADE-R15",
        name="commitment_breach_triggers_severity",
        source_domain="actionops",
        source_subtype="commitment_breached",
        target_domain="reflectionops",
        target_function_id="RE-F08",
        description="Commitment breach triggers centralized severity scoring.",
    ),

    # ActionOps -> IntelOps
    CascadeRule(
        rule_id="CASCADE-R16",
        name="commitment_complete_updates_claims",
        source_domain="actionops",
        source_subtype="commitment_completed",
        target_domain="intelops",
        target_function_id="INTEL-F12",
        description="Commitment completion triggers confidence recalc on related claims.",
    ),

    # ActionOps -> FranOps
    CascadeRule(
        rule_id="CASCADE-R17",
        name="commitment_breach_triggers_canon_review",
        source_domain="actionops",
        source_subtype="commitment_escalated",
        target_domain="franops",
        target_function_id="FRAN-F03",
        description="Escalated commitment triggers canon enforcement review.",
    ),

    # ── Module E: Institutional Memory cascade rules ─────────

    # ReflectionOps -> ReflectionOps (precedent extraction)
    CascadeRule(
        rule_id="CASCADE-R18",
        name="reflection_triggers_precedent",
        source_domain="reflectionops",
        source_subtype="reflection_ingested",
        target_domain="reflectionops",
        target_function_id="RE-F13",
        description="Reflection ingestion triggers precedent extraction.",
    ),

    # ReflectionOps -> ReflectionOps (fingerprint computation)
    CascadeRule(
        rule_id="CASCADE-R19",
        name="precedent_triggers_fingerprint",
        source_domain="reflectionops",
        source_subtype="precedent_stored",
        target_domain="reflectionops",
        target_function_id="RE-F14",
        description="Precedent storage triggers fingerprint computation.",
    ),

    # ReflectionOps -> IntelOps (decay triggers half-life re-evaluation)
    CascadeRule(
        rule_id="CASCADE-R20",
        name="decay_triggers_halflife",
        source_domain="reflectionops",
        source_subtype="knowledge_decayed",
        target_domain="intelops",
        target_function_id="INTEL-F11",
        description="Knowledge decay triggers half-life re-evaluation on linked claims.",
    ),

    # ── Module D: Drift Radar cascade rules ──────────────────

    # Drift Radar -> ReflectionOps (amplified severity)
    CascadeRule(
        rule_id="CASCADE-R21",
        name="amplified_red_triggers_severity",
        source_domain="drift_radar",
        source_subtype="severity_amplified",
        target_domain="reflectionops",
        target_function_id="RE-F08",
        description="Amplified red severity triggers centralized severity re-scoring.",
        severity_filter="red",
    ),

    # Drift Radar -> AuthorityOps (cross-domain correlation)
    CascadeRule(
        rule_id="CASCADE-R22",
        name="correlation_triggers_authority",
        source_domain="drift_radar",
        source_subtype="cross_domain_correlation",
        target_domain="authorityops",
        target_function_id="AUTH-F01",
        description="Cross-domain drift correlation triggers authority evaluation.",
    ),

    # ── Module A: Decision Accounting cascade rules ──────────

    # ActionOps -> ActionOps (completion triggers time-to-decision)
    CascadeRule(
        rule_id="CASCADE-R23",
        name="completion_triggers_ttd",
        source_domain="actionops",
        source_subtype="commitment_completed",
        target_domain="actionops",
        target_function_id="ACTION-F14",
        description="Commitment completion triggers time-to-decision measurement.",
    ),

    # ActionOps -> ActionOps (time measured triggers value assessment)
    CascadeRule(
        rule_id="CASCADE-R24",
        name="ttd_triggers_value",
        source_domain="actionops",
        source_subtype="time_to_decision_measured",
        target_domain="actionops",
        target_function_id="ACTION-F15",
        description="Time-to-decision measurement triggers value assessment.",
    ),

    # ActionOps -> ActionOps (value assessed triggers debt detection)
    CascadeRule(
        rule_id="CASCADE-R25",
        name="value_triggers_debt",
        source_domain="actionops",
        source_subtype="value_assessed",
        target_domain="actionops",
        target_function_id="ACTION-F16",
        description="Value assessment triggers decision debt detection.",
    ),

    # ActionOps -> ReflectionOps (budget overrun triggers severity)
    CascadeRule(
        rule_id="CASCADE-R26",
        name="overrun_triggers_severity",
        source_domain="actionops",
        source_subtype="budget_overrun",
        target_domain="reflectionops",
        target_function_id="RE-F08",
        description="Budget overrun triggers centralized severity scoring.",
    ),

    # ActionOps -> ReflectionOps (debt detected triggers precedent storage)
    CascadeRule(
        rule_id="CASCADE-R27",
        name="debt_triggers_precedent",
        source_domain="actionops",
        source_subtype="decision_debt_detected",
        target_domain="reflectionops",
        target_function_id="RE-F13",
        description="Decision debt triggers precedent storage (learn from costly decisions).",
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
