---
title: "Enterprise Lattice — Credibility Engine at Organizational Scale"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# 02 — Enterprise Lattice

**~500 nodes. Redundancy illusion becomes visible.**

At enterprise scale, the lattice grows from a single claim to multiple decision domains, each with independent claims, shared sources, and cross-domain dependencies. The problems that were visible but manageable at 12 nodes become structural risks that require formal governance.

---

## Guardrails

This example is abstract and non-domain. It does not model real-world weapons or specific industries. It demonstrates institutional credibility architecture only.

---

## What Changes at Enterprise Scale

| Dimension | Mini (12 nodes) | Enterprise (~500 nodes) |
|-----------|----------------|------------------------|
| Claims | 1 top-level | Multiple per domain |
| Quorum | Simple K-of-N | K-of-N with correlation group enforcement |
| Sources | 2, single correlation risk | Dozens, cross-domain sharing |
| Sync | 1 beacon, manual | Per-domain Sync Planes, 2+ beacons |
| Drift | Visible, manual response | Thresholds required, semi-automated |
| Correlation | Obvious | Hidden — requires formal tracking |

---

## Lattice Structure (Abstract)

```
Domain Alpha (Mission Readiness)
├── Claim-A1 (Tier 0) ─── 4 SubClaims ─── 12 Evidence nodes
├── Claim-A2 (Tier 0) ─── 3 SubClaims ─── 9 Evidence nodes
└── Claim-A3 (Tier 1) ─── 2 SubClaims ─── 6 Evidence nodes

Domain Beta (Infrastructure Health)
├── Claim-B1 (Tier 0) ─── 5 SubClaims ─── 15 Evidence nodes
├── Claim-B2 (Tier 1) ─── 3 SubClaims ─── 8 Evidence nodes
└── Claim-B3 (Tier 1) ─── 2 SubClaims ─── 5 Evidence nodes

Domain Gamma (External Compliance)
├── Claim-G1 (Tier 0) ─── 4 SubClaims ─── 10 Evidence nodes
└── Claim-G2 (Tier 1) ─── 3 SubClaims ─── 7 Evidence nodes

Sources: 25 sources across 6 correlation groups
Sync: 3 domain-level Sync Planes, 2 beacons each
```

### Cross-Domain Sharing

Source-S003 feeds evidence into both Domain Alpha and Domain Beta. It appears in 12 claims across 2 domains. If Source-S003 fails:

- 12 evidence nodes lose their source simultaneously
- Claims in Alpha and Beta are correlated through a shared dependency
- The institution may believe Alpha and Beta are independent when they are not

**This is the redundancy illusion.** Two domains look independent. They are not.

---

## Credibility Index at Enterprise Scale

### Tier-Weighted Integrity

8 claims across 3 domains. 4 are Tier 0 (highest weight). All currently have confidence > 0.80. Integrity: **strong baseline**.

### Drift Penalty

2 evidence nodes in Domain Beta have expired TTLs (Tier 1 evidence, TTL was 1 day, last refresh was 36 hours ago). Active drift on Claim-B2.

Penalty: **moderate** (localized to one domain, non-Tier-0 claim).

### Correlation Risk

Source-S003 feeds 12 claims across 2 domains. This is the dominant risk factor at enterprise scale.

Penalty: **significant** (non-linear penalty for cross-domain source concentration).

### Quorum Margin

Most claims have 3-4 evidence sources. Margins are generally healthy (N−K ≥ 2). However, Claim-G2 in Domain Gamma has only 2 sources from the same correlation group — effectively zero independent margin.

Penalty: **moderate** (one claim with structural weakness).

### Independent Confirmation Bonus

Claim-A1 has evidence from 4 sources across 3 correlation groups. Bonus applies.

### Domain Breakdown

| Domain | Sub-Index | Key Risk |
|--------|-----------|----------|
| Alpha | 91 | Source-S003 dependency |
| Beta | 82 | TTL expiration on Claim-B2 |
| Gamma | 87 | Claim-G2 quorum weakness |

### Composite Score

Estimated Credibility Index: **~85** (Minor drift band, approaching elevated risk)

The correlation risk penalty from Source-S003 is the primary drag. Without it, the score would be ~92.

---

## Drift Scenarios

### Scenario 1: Timing Entropy

Domain Beta's primary evidence feed develops variable ingestion lag. The Sync Plane detects that `ingest_time - event_time` variance has increased 40% over the past 6 hours.

- **Category:** Timing entropy
- **Runtime types triggered:** time, contention
- **Impact:** Evidence freshness becomes unreliable for Domain Beta claims
- **Response:** Investigate feed infrastructure, temporarily increase TTLs

### Scenario 2: Confidence Volatility

Source-S003's confidence scores for Domain Alpha evidence fluctuate between 0.65 and 0.92 over a 24-hour period without any known external cause.

- **Category:** Confidence volatility
- **Runtime types triggered:** verify, outcome
- **Impact:** Claims dependent on S003 cannot maintain stable status
- **Response:** Downgrade S003 tier, increase quorum requirement for affected claims

### Scenario 3: External Mismatch

The Sync Plane's Beacon-B2 (external authority) reports timestamps that diverge from Domain Gamma's internal Sync Plane by >500ms consistently.

- **Category:** External mismatch
- **Runtime types triggered:** bypass, verify
- **Impact:** Domain Gamma's evidence ordering may be unreliable
- **Response:** Quarantine Gamma evidence, investigate clock synchronization

---

## Sync Plane at Enterprise Scale

Each domain operates its own Sync Plane:

| Domain | Beacons | Sync Nodes | Watermark Cadence |
|--------|---------|------------|-------------------|
| Alpha | 2 (1 internal, 1 external) | 3 | 30-second window |
| Beta | 2 (both external) | 3 | 15-second window |
| Gamma | 2 (1 internal, 1 external) | 2 | 60-second window |

Cross-domain watermark coordination happens through beacon federation: beacons visible to multiple domains provide a shared time reference.

---

## Deployment Notes

This scale maps to the [MVP deployment pattern](../../docs/credibility-engine/deployment_patterns.md):

- 6–8 engineers
- Single region
- $1.5M–$3M/year
- Semi-automated drift management
