"""Deterministic, standard-library-only evaluator for the synthetic Zipf pilot.

Scores allocate review attention. Gate results evaluate supplied scenario
metadata; they do not establish truth, authenticate identities, or authorize a
real-world action. The evaluator reads no clock, network, or external files.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
import re
from typing import Any


class ValidationError(ValueError):
    """The supplied scenario does not satisfy the pilot input contract."""


_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_ID = re.compile(r"[A-Za-z0-9_.:\-]{1,80}", re.ASCII)
_CONCEPT = re.compile(r"[A-Za-z0-9 _\-]{1,80}", re.ASCII)
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", re.ASCII)
_CONTROLS = re.compile(r"[\x00-\x1f\x7f]")
_GATE_ORDER = (
    "CONTRADICTION",
    "INSUFFICIENT_INDEPENDENT_SUPPORT",
    "MISSING_EVIDENCE_TYPES",
    "MISSING_REVIEW",
    "REVIEW_EXPIRED",
    "REVIEW_REJECTED",
    "REVIEW_ROLE",
    "REVIEW_VERSION",
    "MISSING_AUTHORITY",
    "AUTHORITY_EXPIRED",
    "AUTHORITY_REVOKED",
    "AUTHORITY_ROLE",
    "AUTHORITY_VERSION",
    "AUTHORITY_USE",
)


def _fail(path: str, message: str) -> None:
    raise ValidationError(f"{path}: {message}")


def _object(value: Any, path: str) -> dict:
    if not isinstance(value, dict):
        _fail(path, "must be an object")
    return value


def _array(value: Any, path: str, minimum: int = 0, maximum: int | None = None) -> list:
    if not isinstance(value, list):
        _fail(path, "must be an array")
    if len(value) < minimum or (maximum is not None and len(value) > maximum):
        end = "unbounded" if maximum is None else str(maximum)
        _fail(path, f"must contain {minimum}..{end} entries")
    return value


def _required(obj: dict, key: str, path: str) -> Any:
    if key not in obj:
        _fail(f"{path}.{key}", "is required")
    return obj[key]


def _integer(value: Any, path: str, minimum: int, maximum: int) -> int:
    # JSON has one numeric type. Accept 5.0 as an integer, as JSON Schema and
    # JavaScript do, while explicitly rejecting Python's bool-as-int behavior.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(path, "must be an integer")
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        _fail(path, "must be a finite integer")
    if not minimum <= value <= maximum:
        _fail(path, f"must be between {minimum} and {maximum}")
    return int(value)


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _fail(path, "must be a boolean")
    return value


def _identifier(value: Any, path: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        _fail(path, "must be an ASCII identifier of 1..80 letters, digits, _, ., :, or -")
    return value


def _label(value: Any, path: str) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= 80
            or not value.strip() or _CONTROLS.search(value)):
        _fail(path, "must be a nonblank string of 1..80 characters without controls")
    return value


def _labels(value: Any, path: str, minimum: int = 0) -> list[str]:
    result = [_label(item, f"{path}[{index}]")
              for index, item in enumerate(_array(value, path, minimum))]
    if len(set(result)) != len(result):
        _fail(path, "entries must be unique")
    return result


def _concept(value: Any, path: str) -> str:
    if not isinstance(value, str) or _CONCEPT.fullmatch(value) is None:
        _fail(path, "must be 1..80 ASCII letters, digits, spaces, underscores or hyphens")
    normalized = " ".join(value.lower().split())
    if not normalized:
        _fail(path, "must contain a nonspace character")
    return normalized


def _timestamp(value: Any, path: str) -> datetime:
    if not isinstance(value, str) or _STAMP.fullmatch(value) is None:
        _fail(path, "must be a UTC timestamp in YYYY-MM-DDTHH:MM:SSZ format")
    try:
        return datetime(int(value[0:4]), int(value[5:7]), int(value[8:10]),
                        int(value[11:13]), int(value[14:16]), int(value[17:19]),
                        tzinfo=timezone.utc)
    except ValueError:
        _fail(path, "must be a valid calendar timestamp with year 0001..9999")


def _enum(value: Any, choices: tuple[str, ...], path: str) -> str:
    if not isinstance(value, str) or value not in choices:
        _fail(path, "must be one of " + ", ".join(choices))
    return value


def _policy(value: Any) -> dict:
    path = "policy"
    obj = _object(value, path)
    result = {"id": _identifier(_required(obj, "id", path), "policy.id")}
    bounds = {
        "version": (1, _MAX_SAFE_INTEGER),
        "rarity_cap": (0, 30),
        "min_relevance": (0, 100),
        "min_quality": (0, 100),
        "min_independent_support": (1, 10),
        "max_evidence_age_days": (1, 3650),
    }
    for name, (minimum, maximum) in bounds.items():
        result[name] = _integer(_required(obj, name, path), f"policy.{name}", minimum, maximum)
    for name in ("required_evidence_types", "reviewer_roles", "authority_roles"):
        result[name] = _labels(_required(obj, name, path), f"policy.{name}", 1)
    result["intended_use"] = _label(_required(obj, "intended_use", path), "policy.intended_use")
    return result


def _review_or_authority(value: Any, path: str, authority: bool = False) -> dict | None:
    if value is None:
        return None
    obj = _object(value, path)
    id_key = "authority_id" if authority else "reviewer_id"
    result = {
        id_key: _identifier(_required(obj, id_key, path), f"{path}.{id_key}"),
        "role": _label(_required(obj, "role", path), f"{path}.role"),
        "expires_at": _timestamp(_required(obj, "expires_at", path), f"{path}.expires_at"),
    }
    for name in ("claim_version", "policy_version"):
        result[name] = _integer(_required(obj, name, path), f"{path}.{name}", 1, _MAX_SAFE_INTEGER)
    if authority:
        result["intended_use"] = _label(_required(obj, "intended_use", path), f"{path}.intended_use")
        result["revoked"] = _boolean(_required(obj, "revoked", path), f"{path}.revoked")
    else:
        result["decision"] = _enum(_required(obj, "decision", path), ("approved", "rejected"), f"{path}.decision")
    return result


def _validate(payload: Any) -> dict:
    obj = _object(payload, "payload")
    if _required(obj, "schema_version", "payload") != "1.0":
        _fail("schema_version", 'must be exactly "1.0"')
    as_of_text = _required(obj, "as_of", "payload")
    as_of = _timestamp(as_of_text, "as_of")
    budget = _integer(_required(obj, "review_budget", "payload"), "review_budget", 1, 100)
    policy = _policy(_required(obj, "policy", "payload"))

    aliases = {}
    raw_aliases = _object(_required(obj, "aliases", "payload"), "aliases")
    for key, value in raw_aliases.items():
        normalized_key = _concept(key, "aliases.key")
        normalized_value = _concept(value, f"aliases[{key!r}]")
        if normalized_key in aliases:
            _fail("aliases", "normalized keys must be unique")
        aliases[normalized_key] = normalized_value
    if any(target in aliases for target in aliases.values()):
        _fail("aliases", "cycles and chained mappings are not permitted")

    claims = []
    claim_ids = set()
    # Shared identity across report and evidence declarations prevents one
    # originating event being reassigned to a different claim by copying it.
    event_owner: dict[tuple[str, str], str] = {}

    def register_event(origin_id: str, event_id: str, claim_id: str, path: str) -> None:
        pair = (origin_id, event_id)
        if pair in event_owner and event_owner[pair] != claim_id:
            _fail(path, "origin_id/event_id pair is already assigned to another claim")
        event_owner[pair] = claim_id

    raw_claims = _array(_required(obj, "claims", "payload"), "claims", 1, 1000)
    for index, raw_claim in enumerate(raw_claims):
        path = f"claims[{index}]"
        claim = _object(raw_claim, path)
        claim_id = _identifier(_required(claim, "id", path), f"{path}.id")
        if claim_id in claim_ids:
            _fail(f"{path}.id", "claim IDs must be unique")
        claim_ids.add(claim_id)
        concept = _concept(_required(claim, "concept", path), f"{path}.concept")
        statement = _required(claim, "statement", path)
        if not isinstance(statement, str) or not 1 <= len(statement) <= 2000:
            _fail(f"{path}.statement", "must be a string of 1..2000 characters")
        result = {
            "id": claim_id,
            "version": _integer(_required(claim, "version", path), f"{path}.version", 1, _MAX_SAFE_INTEGER),
            "canonical_concept": aliases.get(concept, concept),
            "statement": statement,
            "required_evidence_types": _labels(_required(claim, "required_evidence_types", path), f"{path}.required_evidence_types"),
            "review": _review_or_authority(_required(claim, "review", path), f"{path}.review"),
            "authority": _review_or_authority(_required(claim, "authority", path), f"{path}.authority", True),
        }
        for name in ("relevance", "consequence", "quality"):
            result[name] = _integer(_required(claim, name, path), f"{path}.{name}", 0, 100)
        for name in ("contradiction", "mandatory"):
            result[name] = _boolean(_required(claim, name, path), f"{path}.{name}")

        evidence = []
        evidence_ids = set()
        event_signatures = {}
        for evidence_index, raw_evidence in enumerate(_array(_required(claim, "evidence", path), f"{path}.evidence")):
            epath = f"{path}.evidence[{evidence_index}]"
            entry = _object(raw_evidence, epath)
            item = {name: _identifier(_required(entry, name, epath), f"{epath}.{name}")
                    for name in ("id", "origin_id", "event_id")}
            if item["id"] in evidence_ids:
                _fail(f"{epath}.id", "evidence IDs must be unique within a claim")
            evidence_ids.add(item["id"])
            item.update({
                "kind": _label(_required(entry, "kind", epath), f"{epath}.kind"),
                "stance": _enum(_required(entry, "stance", epath), ("supports", "contradicts", "neutral"), f"{epath}.stance"),
                "claim_version": _integer(_required(entry, "claim_version", epath), f"{epath}.claim_version", 1, _MAX_SAFE_INTEGER),
                "observed_at": _timestamp(_required(entry, "observed_at", epath), f"{epath}.observed_at"),
                "support_assessed": _boolean(_required(entry, "support_assessed", epath), f"{epath}.support_assessed"),
            })
            register_event(item["origin_id"], item["event_id"], claim_id, epath)
            pair = (item["origin_id"], item["event_id"])
            signature = tuple(item[name] for name in ("kind", "stance", "claim_version", "observed_at", "support_assessed"))
            if pair in event_signatures and event_signatures[pair] != signature:
                _fail(epath, "evidence sharing an origin/event identity must agree")
            event_signatures[pair] = signature
            evidence.append(item)
        result["evidence"] = evidence
        claims.append(result)

    reports = []
    report_ids = set()
    for index, raw_report in enumerate(_array(_required(obj, "reports", "payload"), "reports", 0, 50000)):
        path = f"reports[{index}]"
        report = _object(raw_report, path)
        item = {name: _identifier(_required(report, name, path), f"{path}.{name}")
                for name in ("id", "claim_id", "origin_id", "event_id")}
        if item["id"] in report_ids:
            _fail(f"{path}.id", "report IDs must be unique")
        report_ids.add(item["id"])
        if item["claim_id"] not in claim_ids:
            _fail(f"{path}.claim_id", "must refer to an existing claim")
        register_event(item["origin_id"], item["event_id"], item["claim_id"], path)
        reports.append(item)
    return {"as_of": as_of, "as_of_text": as_of_text, "review_budget": budget,
            "policy": policy, "claims": claims, "reports": reports}


def _gate(claim: dict, policy: dict, as_of: datetime) -> tuple[dict, bool]:
    reasons = set()
    supporting_origins = set()
    covered_types = set()
    excluded = []
    unassessed_contradiction = False
    if claim["contradiction"]:
        reasons.add("CONTRADICTION")

    max_age_seconds = policy["max_evidence_age_days"] * 86400
    for evidence in sorted(claim["evidence"], key=lambda item: item["id"]):
        exclusion = None
        age_seconds = (as_of - evidence["observed_at"]).total_seconds()
        if evidence["claim_version"] != claim["version"]:
            exclusion = "VERSION_MISMATCH"
        elif age_seconds < 0:
            exclusion = "FUTURE_EVIDENCE"
        elif age_seconds > max_age_seconds:
            exclusion = "STALE_EVIDENCE"
        elif evidence["stance"] == "supports" and not evidence["support_assessed"]:
            exclusion = "UNASSESSED_SUPPORT"
        if exclusion:
            excluded.append({"id": evidence["id"], "reason": exclusion})
            continue
        if evidence["stance"] == "contradicts":
            reasons.add("CONTRADICTION")
            unassessed_contradiction |= not evidence["support_assessed"]
        elif evidence["stance"] == "supports":
            supporting_origins.add(evidence["origin_id"])
            covered_types.add(evidence["kind"])

    if len(supporting_origins) < policy["min_independent_support"]:
        reasons.add("INSUFFICIENT_INDEPENDENT_SUPPORT")
    required_types = set(policy["required_evidence_types"]) | set(claim["required_evidence_types"])
    missing_types = sorted(required_types - covered_types)
    if missing_types:
        reasons.add("MISSING_EVIDENCE_TYPES")

    review = claim["review"]
    if review is None:
        reasons.add("MISSING_REVIEW")
    else:
        if review["expires_at"] <= as_of:
            reasons.add("REVIEW_EXPIRED")
        if review["decision"] != "approved":
            reasons.add("REVIEW_REJECTED")
        if review["role"] not in policy["reviewer_roles"]:
            reasons.add("REVIEW_ROLE")
        if review["claim_version"] != claim["version"] or review["policy_version"] != policy["version"]:
            reasons.add("REVIEW_VERSION")

    authority = claim["authority"]
    if authority is None:
        reasons.add("MISSING_AUTHORITY")
    else:
        if authority["expires_at"] <= as_of:
            reasons.add("AUTHORITY_EXPIRED")
        if authority["revoked"]:
            reasons.add("AUTHORITY_REVOKED")
        if authority["role"] not in policy["authority_roles"]:
            reasons.add("AUTHORITY_ROLE")
        if authority["claim_version"] != claim["version"] or authority["policy_version"] != policy["version"]:
            reasons.add("AUTHORITY_VERSION")
        if authority["intended_use"] != policy["intended_use"]:
            reasons.add("AUTHORITY_USE")

    return {
        "status": "HOLD" if reasons else "ELIGIBLE",
        "simulated": True,
        "reasons": [reason for reason in _GATE_ORDER if reason in reasons],
        "independent_support_origins": sorted(supporting_origins),
        "missing_evidence_types": missing_types,
        "excluded_evidence": excluded,
    }, unassessed_contradiction


def evaluate(payload: Any) -> dict:
    """Validate and evaluate a scenario without mutating it.

    Raises ValidationError for malformed inputs. The result is JSON-compatible,
    deterministic, and independent of optional evaluator ground-truth labels.
    ELIGIBLE describes only a simulated metadata check, never verification.
    """
    data = _validate(payload)
    claims = data["claims"]
    reports = data["reports"]
    policy = data["policy"]
    claim_by_id = {claim["id"]: claim for claim in claims}
    raw_counts = Counter(report["claim_id"] for report in reports)
    unique_by_claim: dict[str, set[tuple[str, str]]] = {claim["id"]: set() for claim in claims}
    for report in reports:
        unique_by_claim[report["claim_id"]].add((report["origin_id"], report["event_id"]))
    concept_counts = Counter()
    for claim_id, events in unique_by_claim.items():
        concept_counts[claim_by_id[claim_id]["canonical_concept"]] += len(events)
    total_events = sum(len(events) for events in unique_by_claim.values())

    items = []
    for claim in sorted(claims, key=lambda value: value["id"]):
        claim_id = claim["id"]
        concept = claim["canonical_concept"]
        df = concept_counts[concept]
        independent_events = len(unique_by_claim[claim_id])
        base = (45 * claim["relevance"] + 35 * claim["consequence"] + 20 * claim["quality"]) // 100
        popularity_bonus = min(20, 4 * ((1 + df).bit_length() - 1)) if independent_events else 0
        baseline = base + popularity_bonus
        thresholds_met = claim["relevance"] >= policy["min_relevance"] and claim["quality"] >= policy["min_quality"]
        bonus = 0
        if independent_events >= 1 and thresholds_met and df >= 1 and total_events > 1:
            bonus = policy["rarity_cap"] * (total_events - df) // (total_events - 1)
        gate, unassessed_contradiction = _gate(claim, policy, data["as_of"])
        reasons = []
        if claim["mandatory"]:
            reasons.append("MANDATORY_REVIEW")
        if raw_counts[claim_id] > independent_events:
            reasons.append("DUPLICATE_REPORTS_COLLAPSED")
        if independent_events == 0:
            reasons.append("NO_REPORT_OBSERVATIONS")
        if bonus > 0:
            reasons.append("RARITY_BONUS_APPLIED")
        if not thresholds_met:
            reasons.append("RARITY_THRESHOLD_NOT_MET")
        if unassessed_contradiction:
            reasons.append("UNASSESSED_CONTRADICTION")
        items.append({
            "id": claim_id, "statement": claim["statement"], "canonical_concept": concept,
            "mandatory": claim["mandatory"], "relevance": claim["relevance"],
            "consequence": claim["consequence"], "quality": claim["quality"],
            "base_score": base, "baseline_score": baseline, "rarity_bonus": bonus,
            "compensated_score": base + bonus, "report_count": raw_counts[claim_id],
            "independent_events": independent_events, "concept_events": df,
            "reasons": reasons, "gate": gate,
        })

    mandatory = [item["id"] for item in items if item["mandatory"]]
    candidates = [item for item in items if not item["mandatory"]]

    def mode(score_key: str, gate_applied: bool) -> dict:
        ranked = sorted(candidates, key=lambda item: (-item[score_key], -item["consequence"], item["id"]))
        review_ids = [item["id"] for item in ranked[:data["review_budget"]]]
        return {"mandatory_ids": list(mandatory), "review_ids": review_ids,
                "selected_ids": mandatory + review_ids, "gate_applied": gate_applied}

    return {
        "schema_version": "1.0", "as_of": data["as_of_text"],
        "policy": {"id": policy["id"], "version": policy["version"]},
        "items": items,
        "modes": {"baseline": mode("baseline_score", False),
                  "compensated": mode("compensated_score", False),
                  "full_control": mode("compensated_score", True)},
        "diagnostics": {"report_count": len(reports), "unique_events": total_events,
                        "duplicate_reports": len(reports) - total_events,
                        "claims": len(claims), "mandatory_count": len(mandatory),
                        "review_budget": data["review_budget"]},
    }
