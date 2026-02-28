# IntelOps — Claim Lifecycle Automation

> The atomic loop: **ingest -> validate -> drift -> patch -> MG update**.

## Overview

IntelOps is the first of three executable domain modes. It wraps existing FEEDS consumers (ClaimValidator, ClaimTriggerPipeline, AuthorityGateConsumer, EvidenceCheckConsumer, TriageStore) into 12 function handlers keyed by `INTEL-F01` through `INTEL-F12`.

**Module**: `src/core/modes/intelops.py`

## Function Map

| ID | Name | Purpose |
|----|------|---------|
| INTEL-F01 | `claim_ingest` | Ingest a new claim into the canon store and memory graph |
| INTEL-F02 | `claim_validate` | Validate a claim for contradictions, TTL, and consistency |
| INTEL-F03 | `claim_drift_detect` | Record drift from claim validation failures |
| INTEL-F04 | `claim_patch_recommend` | Generate a patch recommendation from a drift signal |
| INTEL-F05 | `claim_mg_update` | Update the Memory Graph with claim/drift/patch nodes |
| INTEL-F06 | `claim_canon_promote` | Promote a validated claim to canon entry (confidence gated) |
| INTEL-F07 | `claim_authority_check` | Verify claim action is blessed by authority slice |
| INTEL-F08 | `claim_evidence_verify` | Verify claim evidence references exist in packet manifest |
| INTEL-F09 | `claim_triage` | Triage drift signals by severity |
| INTEL-F10 | `claim_supersede` | Supersede a claim when a retcon or newer evidence arrives |
| INTEL-F11 | `claim_half_life_check` | Sweep claims for TTL expiry based on half-life |
| INTEL-F12 | `claim_confidence_recalc` | Recalculate claim confidence based on evidence freshness and contradiction density |

## Core Pipeline

```
INTEL-F01 (ingest) -> INTEL-F02 (validate) -> INTEL-F03 (drift detect)
                                                  |
                                                  v
                      INTEL-F05 (MG update) <- INTEL-F04 (patch recommend)
```

Branching from INTEL-F02:
- INTEL-F06: canon promote (confidence >= 0.7)
- INTEL-F07: authority check
- INTEL-F08: evidence verify
- INTEL-F11: half-life check
- INTEL-F12: confidence recalc

## Confidence Decay Model (INTEL-F12)

Simple decay: `-0.1` per contradiction, `-0.01` per day of evidence age. Emits `confidence_decay` drift signal when score drops. Severity is `yellow` if score >= 0.3, `red` otherwise.

## Patch Type Mapping (INTEL-F04)

| Drift Type | Patch Type |
|------------|------------|
| `authority_mismatch` | `authority_update` |
| `freshness` | `ttl_change` |
| `process_gap` | `manual_review` |
| `confidence_decay` | `manual_review` |
| `time` | `dte_change` |
| `fallback` | `cache_bundle_change` |
| `verify` | `verification_change` |
| `outcome` | `action_scope_tighten` |

## Cascade Interactions

IntelOps is a **source** for:
- CASCADE-R01: Claim contradiction -> FranOps canon enforcement
- CASCADE-R02: Claim supersede -> FranOps canon supersede

IntelOps is a **target** for:
- CASCADE-R04: FranOps retcon cascade -> INTEL-F12 confidence recalc
- CASCADE-R05: ReflectionOps episode freeze -> INTEL-F11 half-life check

## Context Dependencies

Every handler receives `event` and `ctx`. Key context fields:

| Key | Type | Used By |
|-----|------|---------|
| `canon_store` | CanonStore | F01, F05, F06, F10 |
| `memory_graph` | MemoryGraph | F01, F03, F04, F05, F10 |
| `drift_collector` | DriftSignalCollector | F03 |
| `triage_store` | TriageStore | F09 |
| `claims` | dict | F02, F12 |
| `canon_claims` | list | F02 |
| `blessed_claims` | set | F07 |
| `manifest_artifacts` | set | F08 |
| `all_claims` | list | F11 |
| `promotion_threshold` | float | F06 (default 0.7) |

## Related Pages

- [FranOps](FranOps) — canon enforcement domain
- [ReflectionOps](ReflectionOps) — gate enforcement domain
- [Cascade Engine](Cascade-Engine) — cross-domain propagation
- [Event Contracts](Event-Contracts) — routing table and event declarations
- [Unified Atomic Claims](Unified-Atomic-Claims) — the Claim primitive
- [Drift to Patch](Drift-to-Patch) — drift lifecycle
