---
title: "Credibility Index — Formal Specification"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-19"
---

# Credibility Index

The Credibility Index is a composite score (0–100) measuring the structural integrity of an institution's claim lattice. It answers one question: **can the institution trust its own assertions right now?**

---

## Components

### 1. Tier-Weighted Claim Integrity

Claims are assigned tiers (0–3). Higher tiers represent foundational institutional assertions; lower tiers represent derived or supporting claims. The integrity score weights higher-tier claims more heavily.

| Tier | Weight | Example Role |
|------|--------|-------------|
| 0 | Highest | Primary institutional assertion |
| 1 | High | Direct supporting evidence |
| 2 | Moderate | Derived or secondary evidence |
| 3 | Low | Supplementary or contextual |

### 2. Drift Penalty

Applied when drift signals are active against claims in the lattice. Severity-weighted:

| Drift Severity | Penalty per Affected Claim |
|---------------|---------------------------|
| Green | Minor |
| Yellow | Moderate |
| Red | Major |

Penalties compound across connected claims in the graph. A red drift on a Tier 0 claim cascades through all dependent subclaims.

### 3. Correlation Risk Penalty

When multiple claims depend on the same source, correlation risk increases. The penalty grows non-linearly — a source feeding 2 claims is acceptable; a source feeding 20 claims is structural risk.

If that single source fails, every dependent claim degrades simultaneously. The Credibility Index penalizes this concentration.

### 4. Quorum Margin Compression

Each claim should have multiple independent evidence sources. The quorum margin is the difference between available sources (N) and required agreement (K). When N−K approaches 1, the lattice is fragile — one source loss breaks quorum.

The penalty increases as the margin compresses toward zero.

### 5. TTL Expiration Penalty

Evidence past its TTL is stale. The penalty is proportional to:

- How many evidence nodes are expired
- How far past TTL they are (recently expired = small penalty; long-expired = large penalty)

No TTL = no truth.

### 6. Independent Confirmation Bonus

Claims confirmed by 3+ independent sources (different tiers, different provenance chains, different correlation groups) receive a bonus. This rewards structural redundancy and reduces fragility.

---

## Interpretation Bands

| Score | Band | Meaning | Recommended Action |
|-------|------|---------|-------------------|
| 95–100 | Stable | All claims well-sourced, no active drift | Monitor |
| 85–94 | Minor drift | Some evidence aging or thin quorum margins | Review flagged claims |
| 70–84 | Elevated risk | Structural gaps or active drift signals | Patch required |
| 50–69 | Structural degradation | Multiple drift signals, source loss, quorum compression | Immediate remediation |
| <50 | Compromised | Claim lattice cannot be trusted | Halt dependent decisions |

---

## Operational Thresholds (30,000–40,000 Nodes)

### Healthy Steady State

| Metric | Threshold |
|--------|-----------|
| Drift events/day | 100–400 |
| Silent nodes | <0.1% |
| Late heartbeats | <0.5% |
| Correlated failures | <0.05% |
| Tier 0 drift | ~0/day |

### Elevated Risk

| Metric | Threshold |
|--------|-----------|
| Silent nodes | 0.3–1% |
| Late heartbeats | 1–3% |
| Correlated failures | >0.2% |
| Quorum margin compression | Observed |

### Structural Degradation

| Metric | Threshold |
|--------|-----------|
| Silent nodes | >2–5% |
| Tier 0 UNKNOWN flips | Any |
| Sync plane disagreement | Any |

Collapse territory.

---

## Fail-First Indicators

Systems fail first through instability. Watch for:

| Indicator | Warning Threshold |
|-----------|------------------|
| Heartbeat variance | ↑ 20–50% |
| Correlation coefficient | >0.7–0.9 |
| Quorum margin (N−K) | ≥ 2 → 1 |
| TTL clustering | Observed |
| Confidence variance | ↑ >30% |

Silence comes later.

---

## Relationship to Coherence Score

The Credibility Index is complementary to the existing [Coherence Score](../../core/scoring.py) (0–100, A–F).

| Dimension | Coherence Score | Credibility Index |
|-----------|----------------|-------------------|
| What it measures | Artifact completeness (DLR/RS/DS/MG) | Claim-lattice structural integrity |
| Scope | Single decision or episode set | Institutional lattice (all claims) |
| Primary signals | Policy adherence, outcome health, drift control, memory completeness | Source redundancy, correlation risk, temporal freshness, quorum health |

Both are needed for full governance. The Coherence Score tells you whether individual decisions are well-governed. The Credibility Index tells you whether the institution's truth infrastructure is sound.
