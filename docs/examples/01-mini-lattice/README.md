---
title: "Mini Lattice — Credibility Engine at Minimum Viable Scale"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# 01 — Mini Lattice

**12 nodes. Learn the fundamentals.**

A credibility lattice is a directed graph where Claims decompose into SubClaims, SubClaims link to Evidence, Evidence links to Sources, and a Sync Plane timestamps everything independently.

This example shows the smallest useful lattice: 1 top-level Claim, 3 SubClaims, 5 Evidence nodes, 2 Sources, and 1 Sync Plane beacon. Twelve nodes total.

---

## Guardrails

This example models a **high-consequence, non-domain capability** that must remain:

- Deployable
- Commandable
- Survivable
- Controlled
- Externally credible

...without ever being exercised.

This is an abstract example. No real-world weapon modeling. No operational domain. Pure institutional credibility architecture.

---

## Lattice Structure

```
Claim-A (Tier 0, "System readiness assertion")
├── SubClaim-A1 (Tier 1, "Primary subsystem operational")
│   ├── Evidence-E1 (Source-S1, TTL: 4h, confidence: 0.92)
│   └── Evidence-E2 (Source-S2, TTL: 8h, confidence: 0.88)
├── SubClaim-A2 (Tier 1, "Secondary subsystem operational")
│   └── Evidence-E3 (Source-S1, TTL: 4h, confidence: 0.95)
└── SubClaim-A3 (Tier 2, "Environmental conditions nominal")
    ├── Evidence-E4 (Source-S2, TTL: 1h, confidence: 0.90)
    └── Evidence-E5 (Source-S2, TTL: 1h, confidence: 0.85)

Sources:
  Source-S1 (Tier 1, correlation_group: "internal-sensors")
  Source-S2 (Tier 2, correlation_group: "external-feeds")

Sync Plane:
  Beacon-B1 (Tier 0, independent time reference)
```

### Node Inventory

| Type | Count | IDs |
|------|-------|-----|
| Claim | 1 | Claim-A |
| SubClaim | 3 | SubClaim-A1, A2, A3 |
| Evidence | 5 | Evidence-E1 through E5 |
| Source | 2 | Source-S1, S2 |
| Sync Beacon | 1 | Beacon-B1 |
| **Total** | **12** | |

---

## Credibility Index Walkthrough

### Component 1: Tier-Weighted Claim Integrity

All claims have evidence with confidence ≥ 0.85. Tier 0 claim is well-supported through its subclaims. Integrity score: **high**.

### Component 2: Drift Penalty

No active drift signals in baseline state. Penalty: **0**.

### Component 3: Correlation Risk

Source-S1 feeds Evidence-E1 and E3 (2 claims depend on it). Source-S2 feeds E2, E4, E5 (all 3 subclaims depend on it). S2 is a moderate concentration risk.

Penalty: **minor** (S2 feeds 3 evidence nodes across 3 subclaims).

### Component 4: Quorum Margin

SubClaim-A1 has 2 evidence nodes from 2 different sources — quorum margin is thin but holds (N=2, K=1, margin=1).

SubClaim-A2 has only 1 evidence node — **zero quorum margin**. If Source-S1 fails, this subclaim has no evidence.

Penalty: **moderate** (A2 has no redundancy).

### Component 5: TTL Expiration

Evidence-E4 and E5 have 1-hour TTLs. If this assessment is run 50 minutes after ingest, they are near expiration.

Penalty: **minor** (approaching but not past TTL).

### Component 6: Independent Confirmation Bonus

No claim has 3+ independent sources. Bonus: **0**.

### Composite Score

Estimated Credibility Index: **~88** (Minor drift band)

The mini lattice is structurally fragile. SubClaim-A2 has zero redundancy, and Source-S2 is a correlation risk. At this scale, a single source failure could cascade to UNKNOWN across multiple subclaims.

---

## Key Observations

- **Fragile to source loss.** Losing Source-S1 breaks quorum on SubClaim-A2 entirely.
- **Thin quorum margins.** No subclaim has more than 2 evidence sources.
- **Correlation risk visible.** Source-S2 feeds 3 of 5 evidence nodes — a concentration that would be masked in a larger lattice.
- **Easy to reason about manually.** At 12 nodes, a human can trace every dependency. This does not scale.
- **TTL pressure is real.** Short TTLs (1h) on Tier 2 evidence mean this lattice requires frequent refresh just to maintain baseline.

---

## What This Example Teaches

The mini lattice proves the mechanics:

1. Claims decompose into subclaims
2. Evidence has TTLs that expire
3. Sources belong to correlation groups
4. A Sync Plane provides independent timing
5. Loss of a source can flip a claim to UNKNOWN
6. The Credibility Index quantifies structural health

These same mechanics apply at 500 nodes and 40,000 nodes. The difference is not the model — it is the consequences of scale.

---

## Try It with Existing Tools

```bash
# Score coherence on existing episode data
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json

# Run drift detection
python -m coherence_ops.examples.drift_patch_cycle

# Query institutional memory
python -m coherence_ops iris query --type WHAT_DRIFTED --json
```
