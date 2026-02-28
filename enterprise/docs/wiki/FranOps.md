# FranOps — Canon Enforcement & Retcon Engine

> When the truth changes, the record must change with it — but never silently.

## Overview

FranOps is the canon enforcement domain. It wraps the canon store, workflow state machine, retcon executor, and inflation monitor into 12 function handlers keyed by `FRAN-F01` through `FRAN-F12`.

**Module**: `src/core/modes/franops.py`

## Function Map

| ID | Name | Purpose |
|----|------|---------|
| FRAN-F01 | `canon_propose` | Propose a new canon entry for blessing |
| FRAN-F02 | `canon_bless` | Bless a proposed canon entry with authority verification (auto-activates) |
| FRAN-F03 | `canon_enforce` | Enforce canon rules against active claims and decisions |
| FRAN-F04 | `retcon_assess` | Assess impact of a proposed retroactive correction |
| FRAN-F05 | `retcon_execute` | Execute a retcon: create superseding claim, update canon, seal |
| FRAN-F06 | `retcon_propagate` | Propagate retcon effects to dependent claims and canon entries |
| FRAN-F07 | `inflation_monitor` | Monitor canon inflation thresholds per domain |
| FRAN-F08 | `canon_expire` | Expire canon entries past their `expiresAt` timestamp |
| FRAN-F09 | `canon_supersede` | Supersede a canon entry with a newer version |
| FRAN-F10 | `canon_scope_check` | Validate canon entry scope is consistent across domains |
| FRAN-F11 | `canon_drift_detect` | Detect canon-specific drift: stale, conflicting, orphaned claims |
| FRAN-F12 | `canon_rollback` | Rollback a canon entry to a prior version in the supersedes chain |

## Canon State Machine

```
PROPOSED -[bless]-> BLESSED -[activate]-> ACTIVE
    |                                       |
    v                                       +--[review]--> UNDER_REVIEW --> ACTIVE | SUPERSEDED
  REJECTED                                  +--[retcon]--> RETCONNED
                                            +--[expire]--> EXPIRED
                                            +--[freeze]--> FROZEN
```

**Implementation**: `src/core/feeds/canon/workflow.py`

## Retcon Pipeline (FRAN-F04 -> F05 -> F06)

1. **Assess** (FRAN-F04): Enumerate dependent claims, canon entries, and DLRs. Returns blast-radius classification (low/medium/high/critical).
2. **Execute** (FRAN-F05): Create superseding claim, update canon state to RETCONNED, emit drift signals, record audit trail.
3. **Propagate** (FRAN-F06): Invalidate dependent claims, flag affected episodes, trigger cascade rules.

**Implementation**: `src/core/feeds/canon/retcon_executor.py`

## Inflation Thresholds (FRAN-F07)

Per-domain monitoring with configurable thresholds:

| Metric | Default Threshold |
|--------|-------------------|
| Claim count per canon entry | > 50 |
| Contradiction density | > 10% |
| Avg claim age | > 30 days |
| Supersedes depth | > 5 |

Each breach emits a `canon_inflation` drift signal.

**Implementation**: `src/core/feeds/canon/inflation_monitor.py`

## Cascade Interactions

FranOps is a **target** for:
- CASCADE-R01: IntelOps claim contradiction -> FRAN-F03 canon enforce
- CASCADE-R02: IntelOps claim supersede -> FRAN-F09 canon supersede

FranOps is a **source** for:
- CASCADE-R03: Retcon executed -> ReflectionOps episode flag (RE-F01)
- CASCADE-R04: Retcon cascade -> IntelOps confidence recalc (INTEL-F12)

## Context Dependencies

| Key | Type | Used By |
|-----|------|---------|
| `canon_store` | CanonStore | F01, F05, F09, F12 |
| `workflow` | CanonWorkflow | F01, F02, F05, F08, F09, F12 |
| `memory_graph` | MemoryGraph | F05, F09 |
| `canon_claims` | list | F03 |
| `all_canon_entries` | list | F08, F11 |
| `all_claims` | list | F11 |
| `inflation_thresholds` | dict | F07 |
| `valid_domains` | set | F10 (default: intelops, franops, reflectionops) |

## Related Pages

- [Retcon](Retcon) — retroactive claim correction primitive
- [Canon](Canon) — blessed claim memory
- [IntelOps](IntelOps) — claim lifecycle domain
- [ReflectionOps](ReflectionOps) — gate enforcement domain
- [Cascade Engine](Cascade-Engine) — cross-domain propagation
- [Event Contracts](Event-Contracts) — routing table and event declarations
