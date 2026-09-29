# Deep Sigma ↔ NVIDIA OpenShell

**Status:** integration library v0.1.0  
**Principle:** **OpenShell contains the agent. Deep Sigma contains the consequences.**

## Boundary

OpenShell is the enforcement substrate. Deep Sigma remains the mission, semantic, authority, judgment, provenance, drift, and institutional-memory layer.

```text
Agent Mission Intent
        ↓
DKO / DSAL-ready AgentMissionContract
        ↓
PATHFINDER / AuthorityOps
        ↓
RESONATOR-facing semantic checks
        ↓
COMPOSER projection boundary
        ↓
OpenShell policy YAML
        ↓
OpenShell sandbox / kernel / network enforcement
        ↓
OCSF runtime evidence
        ↓
CERPA: Claim → Event → Review → Patch → Apply
        ↓
VINCULUM replay / institutional memory
```

The integration deliberately does **not** create a Deep Sigma sandbox engine.

## What the Python library provides

`core.openshell` adds:

- `AgentMissionContract` — governed DKO-shaped mission contract.
- `OpenShellPolicyCompiler` — deterministic mission-contract → OpenShell YAML projection.
- `OpenShellSemanticValidator` — conservative RESONATOR-facing preflight checks.
- `DeepSigmaAuthorityAdapter` — routes proposed runtime changes through existing AuthorityOps `RuntimeGate`.
- `diff_policies()` — detects static changes, hot-reloadable changes, and permission expansion.
- `GovernedOpenShellController` — blocks, escalates, requests human approval, recreates or hot-reloads as appropriate.
- `OpenShellCliRuntime` — uses the documented OpenShell CLI for create/get/set/prove/exec/delete.
- `OpenShellSdkProbe` — optional official Python SDK health/exec support without guessing undocumented policy methods.
- `normalize_ocsf_event()` — converts OpenShell OCSF JSON into a stable Deep Sigma runtime event.
- CERPA bridge — converts policy plans and runtime denials into Claim/Event/Review/Patch/Apply cycles.
- VINCULUM projection — replay-safe normalized runtime events with contract and policy hashes.

## Governance invariants

1. **Technical permission is not mission authorization.** OpenShell policy proof never substitutes for Deep Sigma authority.
2. **Access expansion requires review.** New filesystem/network access, broader write access, or new allow rules are marked as expansion.
3. **Medium/large blast radius requires a human gate.** Semantic validation fails closed otherwise.
4. **Static OpenShell controls require recreation.** Filesystem, Landlock and process changes are not hot-reloaded.
5. **Dynamic network policy can be hot-reloaded.** The controller treats it separately from static policy.
6. **Credential-bound endpoints require exact hostnames.** Wildcard DNS authorization is rejected by the contract validator.
7. **Denied runtime behavior becomes evidence.** OpenShell denials feed CERPA rather than being silently patched around.
8. **The agent never rewrites its own authority.** The controller is outside the sandbox/runtime action loop.

## Install

Deep Sigma continues to support Python 3.10+. The OpenShell Python SDK itself requires Python 3.11+, so it is optional. The CLI adapter can be used independently.

```bash
pip install -e .
# Optional on Python 3.11+
pip install openshell
```

The OpenShell CLI/gateway are installed separately according to NVIDIA's installation instructions.

## Compile a mission contract

```bash
deepsigma-openshell compile examples/openshell_agent_mission.yaml \
  --out /tmp/cu-as-policy.yaml \
  --dko-out /tmp/cu-as-contract.dko.json
```

## Programmatic flow

```python
from core.openshell import (
    DeepSigmaAuthorityAdapter,
    GovernedOpenShellController,
    OpenShellCliRuntime,
    load_contract,
)

contract = load_contract("examples/openshell_agent_mission.yaml")
runtime = OpenShellCliRuntime()
authority = DeepSigmaAuthorityAdapter(authority_context)
controller = GovernedOpenShellController(runtime, authority)

plan = controller.plan(contract, sandbox_name="nano-cuas")

# A permission expansion will normally remain pending until a human identity
# is supplied through the host-side governed workflow.
plan = controller.apply(plan, approved_by="ROLE:MISSION-AUTHORITY")
```

## OpenShell source alignment

This adapter follows current OpenShell behavior documented by NVIDIA:

- policy schema version `1`;
- filesystem/Landlock/process are startup-time controls;
- network policies are dynamic/hot-reloadable;
- `openshell policy set ... --wait` replaces the complete sandbox policy;
- policy changes are validated before loading;
- the default posture denies outbound network access unless permitted;
- OCSF records provide runtime audit evidence;
- the official Python SDK package is `openshell` and currently requires Python 3.11+.

Because OpenShell is actively developed, the integration isolates syntax in `OpenShellPolicyCompiler` and runtime calls in `OpenShellCliRuntime` so upstream changes do not contaminate Deep Sigma semantics.
