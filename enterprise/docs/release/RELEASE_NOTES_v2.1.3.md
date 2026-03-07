# Release Notes — v2.1.3 "Primitive Surface"

**Date:** 2026-03-07
**Tag:** [v2.1.3](https://github.com/8ryanWh1t3/DeepSigma/releases/tag/v2.1.3)
**PyPI:** [deepsigma 2.1.3](https://pypi.org/project/deepsigma/2.1.3/)

---

## Summary

v2.1.3 is a major feature release that makes the foundational governance primitives explicit. The CERPA adaptation loop (Claim -> Event -> Review -> Patch -> Apply) is now a first-class surface. Three new domain modes ship (ParadoxOps, DecisionSurface, AuthorityOps extension), bringing the total to 86 domain mode handlers across 5 operational domains. Canonical core primitives (AtomicClaim, DecisionEpisode, DriftSignal, Patch) are formalized with JSON Schema validation. The wiki is fully migrated from RAL to Coherence Ops / OVERWATCH terminology. 446 new tests bring the total to 1,232.

---

## Release Gates

| Gate | Result |
|------|--------|
| All tests pass | PASS (1,232 tests) |
| Constitution Gate | PASS |
| Domain Scrub (GPE) | PASS |
| Edition Guard | PASS |

---

## Headline: CERPA Primitive Layer

**Claim -> Event -> Review -> Patch -> Apply**

CERPA is the foundational adaptation loop for the platform. Every governance flow — across IntelOps, ReOps, FranOps, AuthorityOps, and ActionOps — follows this cycle. Previously implicit across `decision_surface/claim_event_engine.py`, `primitives.py`, `drift_signal.py`, and `memory_graph.py`, the loop is now an explicit, named, testable surface.

### What shipped

| Module | Purpose |
|--------|---------|
| `src/core/cerpa/types.py` | 4 enums: CerpaDomain, CerpaStatus, ReviewVerdict, PatchAction |
| `src/core/cerpa/models.py` | 6 dataclasses: Claim, Event, Review, Patch, ApplyResult, CerpaCycle |
| `src/core/cerpa/engine.py` | Orchestrator: `run_cerpa_cycle()`, `review_claim_against_event()`, `generate_patch_from_review()`, `apply_patch()`, `cycle_to_dict()` |
| `src/core/cerpa/mappers.py` | 7 bidirectional adapters: AtomicClaim, DriftSignal, DLR, DecisionSurface Event/Claim, canonical Patch |
| `src/core/cerpa/__init__.py` | Package re-exports |

### Review logic (deterministic, no ML)

| Condition | Verdict | Patch Action |
|-----------|---------|-------------|
| Event metadata indicates policy violation | `violation` | `strengthen` |
| Event observed_state contains `status: failed` | `mismatch` | `adjust` |
| Claim metadata indicates expiry | `expired` | `expire` |
| None of the above | `aligned` | No patch generated |

### Demos

```bash
python -m src.core.examples.cerpa_contract_demo
python -m src.core.examples.cerpa_agent_supervision_demo
```

### Mappers (bidirectional)

CERPA does not replace existing structures. Mappers bridge between cycle-focused CERPA models and archival canonical primitives:

| Mapper | Direction |
|--------|-----------|
| `claim_from_atomic` / `claim_to_atomic` | AtomicClaim <-> cerpa.Claim |
| `event_from_surface` | decision_surface.Event -> cerpa.Event |
| `review_from_drift` | DriftSignal -> cerpa.Review |
| `review_from_dlr` | DLR -> cerpa.Review |
| `patch_from_canonical` / `patch_to_canonical` | primitives.Patch <-> cerpa.Patch |

---

## New Domain Modes & Extensions

### ParadoxOps (PDX-F01 through PDX-F12) — 12 handlers

Paradox tension detection and management. Models competing truths as tension sets with poles, dimensions, pressure gradients, and imbalance thresholds.

| Handler | Function |
|---------|----------|
| PDX-F01 | Tension set creation |
| PDX-F02 | Pole management |
| PDX-F03 | Dimension attachment |
| PDX-F04 | Dimension shift |
| PDX-F05 | Pressure computation |
| PDX-F06 | Imbalance computation |
| PDX-F07 | Threshold evaluation |
| PDX-F08 | Drift promotion |
| PDX-F09 | Inter-dimensional drift |
| PDX-F10 | Seal |
| PDX-F11 | Patch |
| PDX-F12 | Lifecycle |

### AuthorityOps Extension (AUTH-F13 through AUTH-F19) — 7 new handlers

Authority drift detection and blast radius simulation extend the existing 12 AuthorityOps handlers to 19.

| Handler | Function |
|---------|----------|
| AUTH-F13 | Authority drift detection |
| AUTH-F14 | Authority history tracking |
| AUTH-F15 | Cross-domain authority correlation |
| AUTH-F16 | Assumption sweep |
| AUTH-F17 | Blast radius computation |
| AUTH-F18 | Blast radius simulation |
| AUTH-F19 | Blast radius propagation |

### DecisionSurface Portable Runtime

Portable Coherence Ops runtime with adapter ABC, claim-event engine (7 evaluation functions), and three adapters: Notebook, CLI, and Vantage.

| Component | Purpose |
|-----------|---------|
| `SurfaceAdapter` ABC | Pluggable runtime interface |
| `ClaimEventEngine` | 7 evaluation functions: evaluate, detect_contradictions, detect_expired_assumptions, etc. |
| `NotebookAdapter` | Jupyter notebook integration |
| `CLIAdapter` | Terminal/CLI integration |
| `VantageAdapter` | Dashboard integration |

### Constraint Executor

Bridges compiled policy rules to runtime evaluation. Connects OpenPQL compiled policies to the domain mode execution path.

---

## Canonical Core Primitives

Formalized the four archival primitives in `src/core/primitives.py` with JSON Schema validation:

| Primitive | Purpose |
|-----------|---------|
| `AtomicClaim` | Schema-validated unit of institutional memory |
| `DecisionEpisode` | Sealed, hash-chained decision envelope |
| `DriftSignal` | Typed drift event with severity, fingerprint, and recurrence |
| `Patch` | Governed correction with rationale and lineage |

Each primitive includes `to_dict()`, `validate()`, `from_dict()`, provenance tracking, and JSON Schema enforcement.

---

## Terminology Migration: RAL -> Coherence Ops / OVERWATCH

17 wiki pages migrated from "Reality Await Layer (RAL)" to "Coherence Ops" / "Sigma OVERWATCH" terminology. All internal and external documentation surfaces now use the canonical names.

### Pages updated

Home, Architecture, Concepts, Quickstart, Contracts, Runtime-Flow, Drift-to-Patch, Coherence-Ops-Mapping, IRIS, Verifiers, Sealing-and-Episodes, Degrade-Ladder, Operations, SLOs-and-Metrics, Replay-and-Testing, Security, FAQ

---

## System Architecture Diagram

Full rewrite of `enterprise/docs/mermaid/01-system-architecture.md`:

- 9 subgraphs: Agents, Core Runtime, Domain Modes, DecisionSurface, FEEDS, Coherence Ops, JRM, Data/Action Planes, Observability + EDGE
- CERPA cycle node with connections from all 5 domain modes
- All 67+ handlers reflected
- Color-coded styling per subsystem

---

## Documentation Updates

| Surface | Change |
|---------|--------|
| Wiki Home | CERPA added to Drift & Governance table |
| Wiki Sidebar | CERPA link in Governance section |
| Wiki Index | CERPA in Runtime + Governance Core |
| Wiki CERPA page | New — loop diagram, primitives, domain table, architecture mapping |
| Feature Catalog | CERPA entry under Core Decision Engine |
| Mermaid 01 | CERPA cycle node + domain mode connections |
| README | CERPA section, System Architecture nav link |
| Palantir Foundry wiki | Full rewrite — architecture, data model, ingestion |
| `docs/architecture/cerpa.md` | ASCII + Mermaid diagrams, 4 mapping tables |
| `src/core/cerpa/README.md` | Package quick-start |

---

## Fixes

| Fix | Commit |
|-----|--------|
| Edition guard false positive on relative imports — added `node.level == 0` check | `9f02522` |
| Pyright type error in `cli_adapter.py` — explicit `dict[str, Any]` annotation | `61ceb6d` |
| `feature_catalog.json` — DECISION_SURFACE moved inside categories array | `7204fa9` |

---

## Test Impact

| Metric | v2.1.2 | v2.1.3 | Delta |
|--------|--------|--------|-------|
| Total tests | 786 | 1,232 | +446 |
| CERPA tests | 0 | 50 | +50 |
| Domain mode tests | — | — | +300+ |
| Primitives tests | 0 | 18 | +18 |

---

## Handler Count

| Domain | Handlers | Status |
|--------|----------|--------|
| IntelOps | 12 (INTEL-F01–F12) | Existing |
| FranOps | 12 (FRAN-F01–F12) | Existing |
| ReflectionOps | 12 (RE-F01–F12) | Existing |
| AuthorityOps | 19 (AUTH-F01–F19) | Extended (+7) |
| ParadoxOps | 12 (PDX-F01–F12) | **New** |
| DecisionSurface | 7 eval functions | **New** |
| Cascade Engine | 13 cross-domain rules | Existing |
| **Total** | **87+** | |

---

## Commits Since v2.1.2

```
3149b30 docs: add CERPA to wiki, sidebar, mermaid architecture, and feature catalog
9f02522 fix: edition guard — skip relative imports in CORE→ENTERPRISE check
6cc34ec feat: add CERPA primitive layer — Claim, Event, Review, Patch, Apply
e443bee feat: add canonical core primitives — AtomicClaim, DecisionEpisode, DriftSignal, Patch
495ed56 docs: add System Architecture link to README nav bar
8e56679 docs: rewrite system architecture diagram — full OVERWATCH system map
7d3ffd8 docs: retire RAL — replace with Coherence Ops / OVERWATCH across wiki
bad7fbc docs: rewrite Palantir Foundry wiki — architecture, data model, ingestion
fca85f5 docs: sync wiki Home, Sidebar, Index with GitHub wiki
ddb7969 docs: update README, wiki, and mermaid for ParadoxOps + DecisionSurface
61ceb6d fix: add explicit dict[str, Any] annotation to fix Pyright type error in cli_adapter.py
7204fa9 fix: feature_catalog.json — move DECISION_SURFACE inside categories array
4b4bf5a feat: DecisionSurface portable Coherence Ops runtime
83136e3 feat: ParadoxOps domain mode — paradox tension sets (PDX-F01–F12)
5f49a5c feat: authority drift detection + blast radius simulation (AUTH-F13–F19)
0658136 feat: constraint executor — bridge compiled rules to runtime evaluation
6ea416e chore: update repo telemetry stats (auto)
```

---

## Upgrade Path

**Consumer action:** None — all changes are additive. Existing APIs, schemas, and contract surfaces are unchanged.

**Rollback:** Yes — v2.1.2 is functionally equivalent for all pre-existing surfaces.

**New surfaces:** CERPA, ParadoxOps, DecisionSurface, extended AuthorityOps, and canonical primitives are opt-in.
