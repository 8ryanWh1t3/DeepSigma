---
title: "Credibility Engine at Scale — Credibility Index Breakdown"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# Credibility Index at Scale

> A single number (0–100) that compresses 40,000 nodes into a decision.

This document applies the formal [Credibility Index](../../docs/credibility-engine/credibility_index.md) specification to a 30,000–40,000 node production lattice.

---

## Component Breakdown

### 1. Tier-Weighted Claim Integrity

At production scale, the lattice contains thousands of claims across tiers:

| Tier | Count (Est.) | Weight | Role |
|------|-------------|--------|------|
| 0 | ~200 | Highest | Foundational institutional assertions |
| 1 | ~800 | High | Direct supporting claims |
| 2 | ~2,000 | Moderate | Derived or secondary claims |
| 3 | ~1,000 | Low | Contextual and reference claims |

Integrity measures: what percentage of claims at each tier have evidence with confidence above threshold and quorum holding?

**Production baseline:** 96% of Tier 0 claims at full integrity, 93% of Tier 1. Weighted integrity contribution: **+42 points** (of 100).

### 2. Drift Penalty

At steady state, the engine processes 100–400 drift events per day. Not all drift signals carry equal weight:

| Severity | Est. Events/Day | Penalty Weight |
|----------|-----------------|---------------|
| Green | 90–360 | Minor (0.01 per event) |
| Yellow | 8–35 | Moderate (0.5 per event) |
| Red | 1–5 | Major (3.0 per event) |

Active drift on a Tier 0 claim cascades through all dependent subclaims. A single red drift on a Tier 0 claim can contribute **−10 to −15 points** to the index.

**Production baseline:** 2 yellow, 0 red active. Drift penalty: **−4 points**.

### 3. Correlation Risk Penalty

The dominant risk factor at institutional scale. The penalty grows non-linearly:

| Source Fan-Out | Penalty Curve |
|---------------|---------------|
| 1–5 claims | Negligible |
| 6–15 claims | Linear growth |
| 16–50 claims | Quadratic growth |
| 50+ claims | Structural risk flag |

At production scale, cross-region sources are the primary concern. A source feeding 30 claims across 2 regions carries more penalty than 3 sources feeding 10 claims each in a single region.

**Production baseline:** 4 sources with fan-out >15, 1 cross-region. Correlation penalty: **−6 points**.

### 4. Quorum Margin Compression

Quorum margin = N − K (available sources minus required agreement).

| Margin | Risk Level | Penalty |
|--------|-----------|---------|
| ≥ 3 | Healthy | 0 |
| 2 | Acceptable | Minor |
| 1 | Fragile | Moderate |
| 0 | Broken (claim → UNKNOWN) | Severe |

At scale, the average quorum margin across Tier 0 claims should be ≥ 3. Any Tier 0 claim with margin = 1 is an immediate remediation target.

**Production baseline:** Average margin 3.2 for Tier 0, 2.4 for Tier 1. 3 claims at margin = 1 (all Tier 2). Quorum penalty: **−2 points**.

### 5. TTL Expiration Penalty

Proportional to:
- Number of expired evidence nodes (breadth)
- How far past TTL (depth)

| Staleness | Penalty per Node |
|-----------|-----------------|
| 0–1× TTL past | Minor |
| 1–3× TTL past | Moderate |
| >3× TTL past | Severe (evidence effectively dead) |

At production scale with 100–400 drift events/day, the automated refresh loop keeps most evidence within TTL. The penalty reflects the gap between refresh rate and TTL discipline.

**Production baseline:** 0.8% of evidence expired (mostly Tier 2/3 with longer TTLs). TTL penalty: **−3 points**.

### 6. Independent Confirmation Bonus

Claims confirmed by 3+ independent sources from different correlation groups receive a structural resilience bonus.

| Independence Level | Bonus |
|-------------------|-------|
| 3 independent sources, 2 regions | +1 per claim |
| 4+ independent sources, 3 regions | +2 per claim |

At production scale, independent confirmation is most impactful for Tier 0 claims. A Tier 0 claim with evidence from 4 sources across 3 regions is structurally resilient to any single-region failure.

**Production baseline:** 140 of 200 Tier 0 claims have 3+ independent sources. Confirmation bonus: **+3 points**.

---

## Composite Score Calculation

| Component | Contribution |
|-----------|-------------|
| Tier-weighted integrity | +42 |
| Drift penalty | −4 |
| Correlation risk | −6 |
| Quorum margin | −2 |
| TTL expiration | −3 |
| Independent confirmation | +3 |
| **Subtotal** | **+30** |
| Base score | +60 |
| **Composite** | **~90** |

**Interpretation:** Minor drift band — healthy for production.

---

## Regional Sub-Indices

The composite score aggregates regional sub-indices weighted by node count and authority share.

| Region | Nodes | Authority | Sub-Index | Primary Drag |
|--------|-------|-----------|-----------|-------------|
| East | 12,000 | 33% | 93 | Source concentration in Domain E2 |
| Central | 14,000 | 39% | 89 | TTL pressure on high-frequency evidence |
| West | 10,000 | 28% | 91 | Thinner quorum margins |
| **Composite** | **36,000** | **100%** | **~90** | |

Central's lower sub-index has the largest drag due to its 39% authority weight. Improving Central's TTL refresh cadence is the highest-leverage action for institutional score improvement.

---

## Score Dynamics

### Steady State Band

At healthy production operation, the Credibility Index oscillates between 85–95:

```
Score
100 ┤
 95 ┤  ╭──╮    ╭──╮    ╭──╮
 90 ┤──╯  ╰────╯  ╰────╯  ╰──  ← Normal oscillation
 85 ┤
 80 ┤              ← Patch-required threshold
 75 ┤
 70 ┤
    └────────────────────────────
    Day 1   Day 2   Day 3   Day 4
```

Dips below 85 trigger review. Dips below 70 trigger remediation. Sustained operation below 50 means the lattice cannot be trusted.

### What Moves the Score

| Event | Impact | Recovery Time |
|-------|--------|--------------|
| Green drift wave (TTL cascade) | −5 to −10 | Minutes (auto-patched) |
| Yellow drift (single region) | −3 to −8 | Hours |
| Red drift (Tier 0 claim) | −10 to −20 | Hours to days |
| Cross-region correlation event | −5 to −15 | Hours |
| Region failure | −15 to −25 | Hours to days |
| Source restoration | +5 to +15 | Immediate on validation |

---

## Relationship to Operational Thresholds

| Credibility Index | Operational Band | Mapping |
|-------------------|-----------------|---------|
| 95–100 | Healthy steady state | Silent nodes <0.1%, late heartbeats <0.5% |
| 85–94 | Normal production | Drift 100–400/day, manageable |
| 70–84 | Elevated risk | Silent nodes 0.3–1%, quorum compression observed |
| 50–69 | Structural degradation | Silent nodes >2%, Tier 0 UNKNOWN flips |
| <50 | Compromised | Collapse territory |

See: [Credibility Index specification](../../docs/credibility-engine/credibility_index.md)
