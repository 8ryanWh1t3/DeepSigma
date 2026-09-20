"""Small synthetic scenarios, independent of either engine implementation."""
from copy import deepcopy


AS_OF = "2026-09-20T12:00:00Z"


def evidence(claim_id, number=1, **changes):
    result = {
        "id": f"E_{claim_id}_{number}", "origin_id": f"S_{claim_id}_{number}",
        "event_id": f"OBS_{claim_id}_{number}", "kind": "observation",
        "stance": "supports", "claim_version": 1,
        "observed_at": "2026-09-19T12:00:00Z", "support_assessed": True,
    }
    result.update(changes)
    return result


def claim(claim_id, concept, **changes):
    result = {
        "id": claim_id, "version": 1, "concept": concept,
        "statement": f"Synthetic claim {claim_id}", "relevance": 80,
        "consequence": 80, "quality": 80, "contradiction": False,
        "mandatory": False, "required_evidence_types": [],
        "evidence": [evidence(claim_id, 1), evidence(claim_id, 2)],
        "review": {"reviewer_id": "REVIEWER", "role": "analyst",
                   "claim_version": 1, "policy_version": 1, "decision": "approved",
                   "expires_at": "2026-10-01T00:00:00Z"},
        "authority": {"authority_id": "AUTHORITY", "role": "decision_owner",
                      "claim_version": 1, "policy_version": 1,
                      "intended_use": "synthetic_pilot", "revoked": False,
                      "expires_at": "2026-10-01T00:00:00Z"},
    }
    result.update(changes)
    return result


def payload():
    """Six originating report events: four common, one rare, one mandatory."""
    claims = [claim("A", "Routine"), claim("B", "Exception"),
              claim("C", "Critical", mandatory=True)]
    reports = []
    for cid, count in [("A", 4), ("B", 1), ("C", 1)]:
        for i in range(count):
            reports.append({"id": f"R_{cid}_{i}", "claim_id": cid,
                            "origin_id": f"O_{cid}", "event_id": f"EVENT_{cid}_{i}"})
    return {
        "schema_version": "1.0", "as_of": AS_OF, "review_budget": 1,
        "policy": {"id": "PILOT", "version": 1, "rarity_cap": 12,
                   "min_relevance": 50, "min_quality": 50,
                   "min_independent_support": 2,
                   "required_evidence_types": ["observation"],
                   "max_evidence_age_days": 30, "reviewer_roles": ["analyst"],
                   "authority_roles": ["decision_owner"],
                   "intended_use": "synthetic_pilot"},
        "aliases": {}, "claims": claims, "reports": reports,
    }


def valid_scenarios():
    cases = [("six_event_reference", payload())]
    p = payload()
    for n in range(100):
        p["reports"].append(dict(p["reports"][0], id=f"COPY_{n}"))
    cases.append(("one_hundred_copies", p))
    for n in [0, 1]:
        p = payload()
        p["reports"] = p["reports"][:n]
        cases.append((f"{n}_report", p))
    p = payload()
    p["aliases"] = {"Unusual Event": "exception"}
    p["claims"][1]["concept"] = "  UNUSUAL   EVENT  "
    cases.append(("normalized_alias", p))
    p = payload()
    p["claims"][1]["concept"] = "routine"
    cases.append(("shared_canonical_concept", p))
    p = payload()
    p["claims"][1]["concept"] = "routine"
    p["reports"] = [r for r in p["reports"] if r["claim_id"] != "B"]
    cases.append(("shared_concept_but_no_own_observation", p))
    p = payload()
    p["reports"].append(dict(p["reports"][0], id="RECURRENCE", event_id="NEW_EVENT"))
    cases.append(("genuine_recurrence", p))
    p = payload()
    p["claims"][0]["statement"] = "\U0001F9ED" * 2000
    cases.append(("unicode_statement_max_length", p))
    p = payload()
    for e in p["claims"][0]["evidence"]:
        e["observed_at"] = "2026-08-21T12:00:00Z"
    cases.append(("inclusive_evidence_age_boundary", p))
    p = payload()
    for c in p["claims"]:
        c["mandatory"] = True
    cases.append(("all_mandatory", p))
    for value in [0, 30]:
        p = payload()
        p["policy"]["rarity_cap"] = value
        cases.append((f"rarity_cap_{value}", p))
    for field in ["quality", "relevance"]:
        for value in [49, 50]:
            p = payload()
            p["claims"][1][field] = value
            cases.append((f"{field}_threshold_{value}", p))
    p = payload()
    p["claims"][0]["review"] = None
    p["claims"][0]["authority"] = None
    p["claims"][0]["evidence"] = []
    cases.append(("missing_all_support_and_approvals", p))
    p = payload()
    p["claims"][0]["evidence"][1]["origin_id"] = "S_A_1"
    cases.append(("one_origin_two_events", p))
    p = payload()
    p["claims"][0]["evidence"].append(dict(p["claims"][0]["evidence"][0], id="COPY_E"))
    cases.append(("copied_evidence", p))
    for change, value in [("claim_version", 2), ("observed_at", "2026-09-21T12:00:00Z"),
                          ("observed_at", "2026-08-01T12:00:00Z"), ("support_assessed", False)]:
        p = payload()
        for e in p["claims"][0]["evidence"]:
            e[change] = value
        cases.append((f"support_{change}_{value}", p))
    for assessed in [False, True]:
        p = payload()
        p["claims"][0]["evidence"].append(evidence("A", 3, stance="contradicts", support_assessed=assessed))
        cases.append((f"contradiction_assessed_{assessed}", p))
    p = payload()
    p["claims"][0]["contradiction"] = True
    cases.append(("claim_contradiction_flag", p))
    for component, changes in [
        ("review", {"role": "other"}), ("review", {"claim_version": 2}),
        ("review", {"policy_version": 2}), ("review", {"decision": "rejected"}),
        ("review", {"expires_at": AS_OF}), ("authority", {"role": "other"}),
        ("authority", {"claim_version": 2}), ("authority", {"policy_version": 2}),
        ("authority", {"intended_use": "other_use"}), ("authority", {"revoked": True}),
        ("authority", {"expires_at": AS_OF}),
    ]:
        p = payload()
        p["claims"][0][component].update(changes)
        cases.append((f"{component}_{next(iter(changes))}_{next(iter(changes.values()))}", p))
    p = payload()
    p["policy"]["required_evidence_types"].append("record")
    cases.append(("policy_evidence_floor", p))
    p = payload()
    p["claims"][0]["required_evidence_types"].append("record")
    cases.append(("claim_evidence_extension", p))
    p = payload()
    p["claims"].reverse()
    p["reports"].reverse()
    cases.append(("permuted_input", p))
    p = payload()
    p["labels"] = {"B": {"truth": False, "priority": 99999}, "A": "ignore"}
    cases.append(("labels_are_inert", p))
    return cases


def invalid_scenarios():
    cases = []

    def mutated(name, path, value=None, delete=False):
        p = payload()
        location = p
        for part in path[:-1]:
            location = location[part]
        if delete:
            del location[path[-1]]
        else:
            location[path[-1]] = value
        cases.append((name, p))

    for key in payload():
        mutated(f"missing_top_{key}", [key], delete=True)
    for key in payload()["policy"]:
        mutated(f"missing_policy_{key}", ["policy", key], delete=True)
    for key in payload()["claims"][0]:
        mutated(f"missing_claim_{key}", ["claims", 0, key], delete=True)
    for key in payload()["claims"][0]["evidence"][0]:
        mutated(f"missing_evidence_{key}", ["claims", 0, "evidence", 0, key], delete=True)
    for key in payload()["claims"][0]["review"]:
        mutated(f"missing_review_{key}", ["claims", 0, "review", key], delete=True)
    for key in payload()["claims"][0]["authority"]:
        mutated(f"missing_authority_{key}", ["claims", 0, "authority", key], delete=True)
    for key in payload()["reports"][0]:
        mutated(f"missing_report_{key}", ["reports", 0, key], delete=True)
    for name, path, value in [
        ("wrong_schema", ["schema_version"], "2.0"),
        ("budget_zero", ["review_budget"], 0), ("budget_large", ["review_budget"], 101),
        ("budget_fraction", ["review_budget"], 1.5), ("budget_boolean", ["review_budget"], True),
        ("cap_negative", ["policy", "rarity_cap"], -1), ("cap_large", ["policy", "rarity_cap"], 31),
        ("quality_negative", ["claims", 0, "quality"], -1),
        ("relevance_large", ["claims", 0, "relevance"], 101),
        ("consequence_boolean", ["claims", 0, "consequence"], False),
        ("quality_string", ["claims", 0, "quality"], "80"),
        ("version_zero", ["claims", 0, "version"], 0),
        ("version_unsafe", ["claims", 0, "version"], 9007199254740992),
        ("version_bool", ["policy", "version"], True),
        ("threshold_bool", ["policy", "min_quality"], True),
        ("support_zero", ["policy", "min_independent_support"], 0),
        ("support_large", ["policy", "min_independent_support"], 11),
        ("age_zero", ["policy", "max_evidence_age_days"], 0),
        ("age_large", ["policy", "max_evidence_age_days"], 3651),
        ("contradiction_nonbool", ["claims", 0, "contradiction"], 1),
        ("mandatory_nonbool", ["claims", 0, "mandatory"], "false"),
        ("assessed_nonbool", ["claims", 0, "evidence", 0, "support_assessed"], 1),
        ("revoked_nonbool", ["claims", 0, "authority", "revoked"], 0),
        ("empty_claims", ["claims"], []), ("claims_not_array", ["claims"], {}),
        ("reports_not_array", ["reports"], {}), ("unknown_claim_report", ["reports", 0, "claim_id"], "MISSING"),
        ("invalid_identifier", ["claims", 0, "id"], "A B"),
        ("identifier_trailing_lf", ["claims", 0, "id"], "A\n"),
        ("empty_statement", ["claims", 0, "statement"], ""),
        ("long_statement", ["claims", 0, "statement"], "x" * 2001),
        ("concept_punctuation", ["claims", 0, "concept"], "Routine!"),
        ("concept_trailing_lf", ["claims", 0, "concept"], "Routine\n"),
        ("empty_concept", ["claims", 0, "concept"], "  "),
        ("empty_policy_types", ["policy", "required_evidence_types"], []),
        ("duplicate_types", ["policy", "required_evidence_types"], ["observation", "observation"]),
        ("empty_roles", ["policy", "reviewer_roles"], []),
        ("duplicate_roles", ["policy", "authority_roles"], ["decision_owner", "decision_owner"]),
        ("invalid_stance", ["claims", 0, "evidence", 0, "stance"], "asserted"),
        ("invalid_review_decision", ["claims", 0, "review", "decision"], "yes"),
        ("long_role", ["claims", 0, "review", "role"], "r" * 81),
        ("long_use", ["claims", 0, "authority", "intended_use"], "u" * 81),
        ("missing_utc", ["as_of"], "2026-09-20T12:00:00"),
        ("invalid_date", ["as_of"], "2026-02-30T12:00:00Z"),
        ("offset_timestamp", ["as_of"], "2026-09-20T12:00:00+00:00"),
        ("timestamp_trailing_lf", ["as_of"], "2026-09-20T12:00:00Z\n"),
        ("alias_cycle", ["aliases"], {"a": "b", "b": "a"}),
        ("alias_chain", ["aliases"], {"a": "b", "b": "c"}),
        ("normalized_duplicate_alias", ["aliases"], {"Some Concept": "a", " some  concept ": "b"}),
        ("alias_invalid_target", ["aliases"], {"a": "b!"}),
    ]:
        mutated(name, path, value)
    p = payload()
    p["claims"].append(deepcopy(p["claims"][0]))
    cases.append(("duplicate_claim_id", p))
    p = payload()
    p["reports"].append(deepcopy(p["reports"][0]))
    cases.append(("duplicate_report_id", p))
    p = payload()
    p["claims"][0]["evidence"].append(deepcopy(p["claims"][0]["evidence"][0]))
    cases.append(("duplicate_evidence_id", p))
    p = payload()
    p["reports"].append(dict(p["reports"][0], id="CROSS_CLAIM", claim_id="B"))
    cases.append(("report_event_cross_claim", p))
    p = payload()
    p["claims"][1]["evidence"].append(dict(p["claims"][0]["evidence"][0], id="CROSS_EVIDENCE"))
    cases.append(("evidence_event_cross_claim", p))
    for key, value in [("kind", "record"), ("stance", "contradicts"),
                       ("claim_version", 2), ("observed_at", "2026-09-18T12:00:00Z"),
                       ("support_assessed", False)]:
        p = payload()
        p["claims"][0]["evidence"].append(dict(p["claims"][0]["evidence"][0], id="COPY", **{key: value}))
        cases.append((f"inconsistent_copy_{key}", p))
    return cases
