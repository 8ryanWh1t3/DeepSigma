from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from core.openshell import (
    AccessMode,
    AgentMissionContract,
    AllowAuthorityAdapter,
    ContractValidationError,
    EndpointPermission,
    GovernanceError,
    GovernedOpenShellController,
    L7Rule,
    OpenShellPolicyCompiler,
    OpenShellSemanticValidator,
    diff_policies,
    normalize_ocsf_event,
    run_runtime_event_cycle,
    to_cerpa_event,
    to_vinculum_event,
)
from core.openshell.loader import contract_from_dict


def make_contract(**overrides):
    data = dict(
        contract_id="AMC-001",
        episode_id="EP-001",
        mission="C-UAS analysis",
        objective="Analyze bounded Lattice evidence",
        agent_id="agent-01",
        actor_id="agent-001",
        command=["python", "-m", "worker"],
        authority_scope="cuas/read",
        blast_radius_tier="small",
        read_only_paths=["/mission/lattice"],
        read_write_paths=["/sandbox/output"],
        evidence_refs=["EV-1"],
        kill_conditions=["stop on authority expansion"],
        endpoints=[
            EndpointPermission(
                name="github-read",
                host="api.github.com",
                access=AccessMode.READ_ONLY.value,
                binaries=["/usr/bin/curl"],
            )
        ],
        human_approval_required=True,
    )
    data.update(overrides)
    return AgentMissionContract(**data)


class FakeRuntime:
    def __init__(self, exists=False, current=None):
        self.exists = exists
        self.current = current
        self.calls = []

    def sandbox_exists(self, name):
        return self.exists

    def get_base_policy(self, name):
        return self.current

    def create_sandbox(self, name, policy_yaml, command, image=None):
        self.calls.append(("create", name, policy_yaml, list(command), image))
        self.exists = True
        self.current = yaml.safe_load(policy_yaml)
        return {"ok": True, "action": "create"}

    def apply_policy(self, name, policy_yaml, *, wait=True):
        self.calls.append(("set", name, policy_yaml, wait))
        self.current = yaml.safe_load(policy_yaml)
        return {"ok": True, "action": "set"}

    def exec(self, name, argv):
        self.calls.append(("exec", name, argv))
        return {"stdout": "ok"}

    def delete(self, name):
        self.calls.append(("delete", name))
        self.exists = False
        return {"ok": True}


class TestContract:
    def test_hash_deterministic(self):
        c = make_contract()
        assert c.canonical_hash() == c.canonical_hash()
        assert c.canonical_hash().startswith("sha256:")

    def test_reject_relative_path(self):
        c = make_contract(read_only_paths=["relative/path"])
        with pytest.raises(ContractValidationError):
            c.validate()

    def test_reject_ro_rw_overlap(self):
        c = make_contract(read_only_paths=["/x"], read_write_paths=["/x"])
        with pytest.raises(ContractValidationError):
            c.validate()

    def test_reject_credential_wildcard(self):
        ep = EndpointPermission(
            name="bad",
            host="*.example.com",
            credential_bound=True,
            binaries=["/usr/bin/python"],
        )
        c = make_contract(endpoints=[ep])
        with pytest.raises(ContractValidationError):
            c.validate()

    def test_dko_contains_authority_and_projection(self):
        dko = make_contract().to_dko()
        assert dko["kind"] == "AgentMissionContract"
        assert dko["authority"]["scope"] == "cuas/read"
        assert dko["openshell_projection"]["endpoints"][0]["host"] == "api.github.com"


class TestCompiler:
    def test_compile_policy(self):
        p = OpenShellPolicyCompiler().compile(make_contract())
        assert p.policy["version"] == 1
        assert "/mission/lattice" in p.policy["filesystem_policy"]["read_only"]
        assert p.policy["network_policies"]["github-read"]["endpoints"][0]["access"] == "read-only"
        assert p.policy_hash.startswith("sha256:")

    def test_compile_l7_rules(self):
        ep = EndpointPermission(
            name="git-clone",
            host="github.com",
            protocol="rest",
            access=None,
            binaries=["/usr/bin/git"],
            rules=[
                L7Rule("GET", "/**/info/refs*"),
                L7Rule("POST", "/**/git-upload-pack"),
            ],
        )
        p = OpenShellPolicyCompiler().compile(make_contract(endpoints=[ep]))
        endpoint = p.policy["network_policies"]["git-clone"]["endpoints"][0]
        assert "access" not in endpoint
        assert endpoint["rules"][1]["allow"]["method"] == "POST"

    def test_yaml_roundtrip(self):
        p = OpenShellPolicyCompiler().compile(make_contract())
        assert yaml.safe_load(p.yaml_text) == p.policy


class TestDelta:
    def test_added_endpoint_is_expansion(self):
        compiler = OpenShellPolicyCompiler()
        old = compiler.compile(make_contract(endpoints=[])).policy
        new = compiler.compile(make_contract()).policy
        d = diff_policies(old, new)
        assert d.dynamic_changed
        assert d.expands_access
        assert any(r.startswith("network_endpoint_added") for r in d.reasons)

    def test_write_path_is_static_expansion(self):
        compiler = OpenShellPolicyCompiler()
        old = compiler.compile(make_contract(read_write_paths=[])).policy
        new = compiler.compile(make_contract(read_write_paths=["/sandbox/output", "/mission/patch"])).policy
        d = diff_policies(old, new)
        assert d.static_changed
        assert d.requires_recreate
        assert d.expands_access

    def test_contraction_not_expansion(self):
        compiler = OpenShellPolicyCompiler()
        old = compiler.compile(make_contract()).policy
        new = compiler.compile(make_contract(endpoints=[])).policy
        d = diff_policies(old, new)
        assert d.dynamic_changed
        assert not d.expands_access

    def test_read_only_to_full_is_expansion(self):
        compiler = OpenShellPolicyCompiler()
        old = compiler.compile(make_contract()).policy
        ep = EndpointPermission(
            name="github-read",
            host="api.github.com",
            access="full",
            binaries=["/usr/bin/curl"],
        )
        new = compiler.compile(make_contract(endpoints=[ep])).policy
        d = diff_policies(old, new)
        assert d.expands_access
        assert any(r.startswith("network_access_expanded") for r in d.reasons)


class TestSemantic:
    def test_medium_requires_human_gate(self):
        c = make_contract(blast_radius_tier="medium", human_approval_required=False)
        p = OpenShellPolicyCompiler().compile(c)
        a = OpenShellSemanticValidator().assess(c, p)
        assert not a.passed
        assert any(f.code == "HUMAN_GATE_REQUIRED" for f in a.findings)

    def test_broad_write_warns_but_does_not_fail_small_contract(self):
        ep = EndpointPermission(
            name="writer",
            host="api.example.com",
            access="full",
            binaries=["/usr/bin/python"],
        )
        c = make_contract(endpoints=[ep])
        p = OpenShellPolicyCompiler().compile(c)
        a = OpenShellSemanticValidator().assess(c, p)
        assert a.passed
        assert any(f.code == "BROAD_NETWORK_WRITE" for f in a.findings)


class TestController:
    def test_new_permissions_wait_for_human(self):
        rt = FakeRuntime(exists=False)
        ctl = GovernedOpenShellController(rt, AllowAuthorityAdapter())
        plan = ctl.plan(make_contract(), sandbox_name="nano")
        assert plan.requires_human_approval
        assert plan.status == "pending_approval"
        with pytest.raises(GovernanceError):
            ctl.apply(plan)

    def test_approved_plan_creates_sandbox(self):
        rt = FakeRuntime(exists=False)
        ctl = GovernedOpenShellController(rt, AllowAuthorityAdapter())
        plan = ctl.plan(make_contract(), sandbox_name="nano")
        applied = ctl.apply(plan, approved_by="ROLE:MISSION-AUTHORITY")
        assert applied.status == "applied"
        assert rt.calls[0][0] == "create"

    def test_dynamic_contraction_hot_reloads(self):
        compiler = OpenShellPolicyCompiler()
        current = compiler.compile(make_contract()).policy
        rt = FakeRuntime(exists=True, current=current)
        ctl = GovernedOpenShellController(rt, AllowAuthorityAdapter())
        c = make_contract(endpoints=[], human_approval_required=False)
        plan = ctl.plan(c, sandbox_name="nano")
        assert plan.status == "ready"
        assert not plan.delta.static_changed
        applied = ctl.apply(plan)
        assert applied.status == "applied"
        assert rt.calls[-1][0] == "set"

    def test_static_change_requires_recreate(self):
        compiler = OpenShellPolicyCompiler()
        current = compiler.compile(make_contract(read_write_paths=[])).policy
        rt = FakeRuntime(exists=True, current=current)
        ctl = GovernedOpenShellController(rt, AllowAuthorityAdapter())
        c = make_contract(read_write_paths=["/sandbox/output", "/new-write"])
        plan = ctl.plan(c, sandbox_name="nano")
        assert plan.status == "requires_recreate"
        same = ctl.apply(plan, approved_by="ROLE:MISSION-AUTHORITY", recreate=False)
        assert same.status == "requires_recreate"
        assert not rt.calls

    def test_static_change_can_recreate_with_explicit_flag(self):
        compiler = OpenShellPolicyCompiler()
        current = compiler.compile(make_contract(read_write_paths=[])).policy
        rt = FakeRuntime(exists=True, current=current)
        ctl = GovernedOpenShellController(rt, AllowAuthorityAdapter())
        c = make_contract(read_write_paths=["/sandbox/output", "/new-write"])
        plan = ctl.plan(c, sandbox_name="nano")
        applied = ctl.apply(plan, approved_by="ROLE:MISSION-AUTHORITY", recreate=True)
        assert applied.status == "applied"
        assert [x[0] for x in rt.calls] == ["delete", "create"]


class TestAudit:
    def test_normalize_denial(self):
        raw = {
            "timestamp": "2026-09-28T20:00:00Z",
            "decision": "DENIED",
            "action": "HTTP:POST",
            "process": {"file": {"path": "/usr/bin/curl"}},
            "dst_endpoint": {"hostname": "api.github.com", "port": 443},
            "http_request": {"http_method": "POST", "url": {"path": "/repos/x/y/issues"}},
            "policy": {"rule": "github_api", "reason": "method denied"},
        }
        event = normalize_ocsf_event(raw, sandbox_name="nano")
        assert event.denied
        assert event.host == "api.github.com"
        assert event.method == "POST"

        ce = to_cerpa_event(event, contract_id="AMC-001", episode_id="EP-001")
        assert ce.metadata["violation"] is True
        assert ce.observed_state["status"] == "violated"

        ve = to_vinculum_event(event, contract_hash="sha256:c", policy_hash="sha256:p")
        assert ve["contract_hash"] == "sha256:c"
        assert ve["resource"]["path"] == "/repos/x/y/issues"

    def test_denial_runs_cerpa_cycle(self):
        event = normalize_ocsf_event({"decision": "DENIED", "action": "NET:OPEN", "reason": "blocked"})
        cycle = run_runtime_event_cycle(make_contract(), event)
        assert cycle.review.drift_detected is True
        assert cycle.patch is not None


class TestLoader:
    def test_from_dict_rules(self):
        c = contract_from_dict({
            "contract_id": "A",
            "episode_id": "E",
            "mission": "M",
            "objective": "O",
            "agent_id": "G",
            "actor_id": "ACT",
            "command": ["python"],
            "authority_scope": "scope",
            "endpoints": [{
                "name": "x",
                "host": "api.example.com",
                "binaries": ["/usr/bin/python"],
                "rules": [{"method": "GET", "path": "/v1/**"}],
            }],
        })
        assert c.endpoints[0].rules[0].method == "GET"

    def test_source_extensions_preserved(self):
        c = contract_from_dict({
            "contract_id": "A",
            "episode_id": "E",
            "mission": "M",
            "objective": "O",
            "agent_id": "G",
            "actor_id": "ACT",
            "command": ["python"],
            "authority_scope": "scope",
            "future_field": {"x": 1},
        })
        assert c.metadata["source_extensions"]["future_field"] == {"x": 1}
