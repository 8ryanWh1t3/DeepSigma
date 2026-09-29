# Deep Sigma ↔ OpenShell Python Integration v0.1.0

## Purpose

Adds a governed Python bridge between Deep Sigma and NVIDIA OpenShell without turning OpenShell into a competing Deep Sigma product.

**Boundary:** OpenShell contains the agent; Deep Sigma contains the consequences.

## Implemented

- DKO/DSAL-ready `AgentMissionContract`
- deterministic OpenShell policy compiler
- exact-host enforcement for credential-bound endpoints
- static vs dynamic policy classification
- permission-expansion detection
- human gate on access expansion
- AuthorityOps / RuntimeGate adapter
- conservative RESONATOR-facing semantic preflight
- COMPOSER-style one-way policy projection boundary
- CERPA integration for plan/runtime events
- OCSF normalization
- VINCULUM replay projection
- documented OpenShell CLI runtime adapter
- optional official OpenShell Python SDK health/exec probe
- explicit sandbox recreation path for filesystem/Landlock/process changes
- sample Nano Sigma C-UAS mission contract

## Verification

- New OpenShell integration tests: **23/23 PASS**
- Full Deep Sigma regression suite after integration: **1255/1255 PASS**
- `python -m compileall src/core/openshell`: **PASS**
- Example mission contract compilation: **PASS**
- Wheel build with local toolchain / no build isolation: **PASS**
- `ruff`: **not available in the execution environment**, so no ruff claim is made.

## Distribution note

The repository's existing package version remains `2.1.2`; the new integration module reports `core.openshell.__version__ == "0.1.0"`. The included wheel is therefore a **local integrated build**, not a claim that the upstream Deep Sigma release version changed.

The NVIDIA `openshell` Python SDK currently requires Python 3.11+. Deep Sigma itself remains Python 3.10+ compatible; the CLI adapter does not require the SDK package.
