# ParadoxOps — Paradox Tension Detection & Lifecycle Management

> Competing truths exist simultaneously. ParadoxOps detects, scores, and manages them.

## Overview

ParadoxOps is the fifth executable domain mode. It detects competing truths (tensions) in the same operational space, tracks them through lifecycle states, computes pressure and imbalance, and promotes them to drift signals when thresholds are breached. Supports pair (2 poles), triple (3 poles), and higher-order (4+ poles) tension sets with multi-dimensional scoring and inter-dimensional drift detection.

**Module**: `src/core/modes/paradoxops.py`

**Package**: `src/core/paradox_ops/` (7 submodules: models, dimensions, scoring, drift, lifecycle, validators, registry)

## Function Map

| ID | Name | Purpose |
|----|------|---------|
| PDX-F01 | `tension_set_create` | Create a Paradox Tension Set with poles and initial dimensions |
| PDX-F02 | `pole_manage` | Add, remove, or update poles in a tension set |
| PDX-F03 | `dimension_attach` | Attach a common or uncommon dimension to a tension set |
| PDX-F04 | `dimension_shift` | Record a dimension value change with previous value preservation |
| PDX-F05 | `pressure_compute` | Compute pressure score (0.0-1.0) from pole dispersion, dimension strain, threshold proximity, rate of change |
| PDX-F06 | `imbalance_compute` | Compute imbalance vector for pair/triple/higher-order sets |
| PDX-F07 | `threshold_evaluate` | Evaluate dimension thresholds and detect breaches |
| PDX-F08 | `drift_promote` | Promote an elevated tension set to a drift signal |
| PDX-F09 | `interdimensional_drift_detect` | Detect inter-dimensional drift (2+ shifted + governance stale) |
| PDX-F10 | `seal_snapshot` | Seal tension set state with hash and version |
| PDX-F11 | `patch_issue` | Issue a patch with recommended actions |
| PDX-F12 | `lifecycle_transition` | Handle rebalance, archive, and other lifecycle transitions |

## Lifecycle State Machine

```
detected --> active
active --> elevated | sealed | archived
elevated --> promoted_to_drift | sealed | active (de-escalation)
promoted_to_drift --> sealed
sealed --> patched | archived
patched --> rebalanced | archived
rebalanced --> archived
archived --> (terminal)
```

## Core Pipeline

```
PDX-F01 (create) --> PDX-F03 (attach dims) --> PDX-F04 (shift dims)
                                                    |
                                                    v
PDX-F05 (pressure) --> PDX-F07 (thresholds) --> PDX-F09 (ID drift)
        |                       |                    |
        v                       v                    v
PDX-F06 (imbalance)    PDX-F08 (promote)    PDX-F11 (patch)
                               |
                               v
                       PDX-F10 (seal) --> PDX-F12 (lifecycle)
```

## Pressure Score Formula

Weighted combination (0.0-1.0):
- **Pole dispersion** (0.3): variance of pole weights, normalized
- **Dimension strain** (0.3): max |current - previous| across dimensions
- **Threshold proximity** (0.2): 1 - min(distance to threshold)
- **Rate of change** (0.2): count of recently shifted dimensions / total

Pressure >= 0.7 with state `active` triggers automatic transition to `elevated`.

## Imbalance Vector

- **Pair** (2 poles): single value in [-1, +1] — `[w1/(w1+w2) - 0.5] * 2`
- **Triple** (3 poles): 3-vector summing to 0 — `[w_i/sum - 1/3]`
- **Higher-order** (4+): n-vector — `[w_i/sum - 1/n]`

## Inter-Dimensional Drift Detection

Triggered when:
1. 2+ dimensions shifted beyond their threshold
2. 1+ governance-relevant dimensions remain stale (shift < 10% of threshold or no shift)

Produces a red drift signal with shifted/stale dimension lists.

## 6 Common Dimensions

| Dimension | Governance Relevant | Threshold |
|-----------|-------------------|-----------|
| time | No | 0.5 |
| authority | Yes | 0.4 |
| risk | Yes | 0.4 |
| layer | No | 0.5 |
| objective | No | 0.5 |
| resource | No | 0.5 |

Plus 10 uncommon dimensions: reversibility, confidence, visibility, classification, provenance_depth, dependency_density, human_fatigue, legal_exposure, mission_criticality, narrative_volatility.

## Patch Actions (8)

| Action | When Used |
|--------|-----------|
| `increase_control_friction` | Risk elevated |
| `clarify_authority` | Authority stale |
| `add_review_gate` | Risk elevated |
| `split_by_layer` | Layer tension |
| `reduce_irreversibility` | Time compressed + risk high |
| `elevate_visibility` | Visibility low |
| `expire_stale_assumption` | Stale assumption |
| `promote_to_policy_band` | Default escalation |

## Context Dependencies

Every handler receives `event` and `ctx`. Key context fields:

| Key | Type | Used By |
|-----|------|---------|
| `paradox_registry` | ParadoxRegistry | All handlers |
| `tension_lifecycle` | TensionLifecycle | F01, F05, F08, F10-F12 |
| `dimension_registry` | DimensionRegistry | F01, F03 |
| `memory_graph` | MemoryGraph | F01, F08, F10, F11 |
| `now` | str | F01, F04, F10, F11 |

## Related Pages

- [IntelOps](IntelOps) — claim lifecycle domain
- [FranOps](FranOps) — canon enforcement domain
- [ReflectionOps](ReflectionOps) — gate enforcement domain
- [AuthorityOps](AuthorityOps) — authority enforcement domain
- [DecisionSurface](DecisionSurface) — portable Coherence Ops runtime
- [Cascade Engine](Cascade-Engine) — cross-domain propagation
- [Event Contracts](Event-Contracts) — routing table and event declarations
