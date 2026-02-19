---
title: "Deployment Patterns — MVP to Production Scale"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-19"
---

# Deployment Patterns

---

## MVP Implementation

### Minimal Stack

| Component | Purpose | Technology Class |
|-----------|---------|-----------------|
| Event stream | Evidence ingestion, drift signals | Message queue (Kafka, NATS) |
| Graph store | Claim lattice persistence | Graph database (Neo4j, TerminusDB) |
| Quorum service | K-of-N agreement tracking | Stateful service with source registry |
| Drift detection service | Institutional drift category detection | Stream processor with state windows |
| Seal export API | Immutable DecisionEpisode archive | Append-only store with hash chain |

### Must Include

- TTL enforcement on every evidence node
- K-of-N quorum with minimum 2 correlation groups
- Correlation group tracking across sources
- Drift detection (at least timing entropy + correlation drift)
- Patch lineage (every correction traceable to its drift signal)
- DecisionEpisode export (sealed, hashed, versioned)

### Team

6–8 engineers:

| Role | Count | Focus |
|------|-------|-------|
| Backend | 2 | Graph store + stream processing |
| Infrastructure | 1 | Deployment, monitoring, sync plane |
| Data | 1 | Evidence ingestion, TTL management |
| Security | 1 | Sealing, signature verification, access control |
| Product / Governance | 1–2 | Drift thresholds, operational playbooks |

### Budget

**$1.5M–$3M/year** (team + infrastructure + tooling)

### Deployment Profile

- Single region
- Single Sync Plane
- 2 time beacons minimum
- Drift detection on 15-minute cycle
- Manual patch review for all severities

---

## Production Deployment

### Requirements (Non-Negotiable)

| Requirement | Detail |
|-------------|--------|
| Regions | 3+ |
| Authority distribution | No single region holds >40% of quorum authority |
| Failure domain isolation | Independent infrastructure per region |
| Sync domains | Independent Sync Plane per region, federated cross-region |
| Evidence temperature | Hot / Warm / Cold separation |
| Drift automation | Required (manual-only is a production risk) |
| Sealed episodes | Mandatory for all decision classes |

### Evidence Temperature Tiers

| Temperature | What It Holds | Retention |
|-------------|--------------|-----------|
| Hot | Active claims, <24h evidence, live Sync Plane | Real-time access |
| Warm | Claims referenced in last 30 days, evidence within TTL | Near-line access |
| Cold | Sealed archive, read-only, hash-verified | Long-term storage |

### Node Scale

30,000–40,000 active nodes across all regions. A "node" is any entity in the lattice: Claim, SubClaim, Evidence, Source, SyncNode.

### Budget

**$6M–$10M/year**

| Category | Range |
|----------|-------|
| Team (20+ engineers, SRE, governance) | $3M–$5M |
| Infrastructure (multi-region compute, storage, network) | $2M–$3M |
| Tooling + licensing | $1M–$2M |

---

## Economic Modeling

### Cost Per Node

**~$170–$280/year** at production scale.

Includes compute, storage, sync overhead, and operational labor amortized across nodes. The range reflects infrastructure choices (cloud vs. on-premise) and operational maturity.

### What the Credibility Engine Prevents

| Loss Category | Without Engine | With Engine |
|---------------|---------------|-------------|
| Decision rework | Frequent — stale decisions re-litigated | Rare — drift caught at deviation |
| Institutional amnesia | Progressive — reasoning lost with personnel | Prevented — Memory Graph + IRIS |
| Correlated blind spots | Invisible — shared dependencies untracked | Visible — correlation risk penalty |
| Silent drift collapse | Catastrophic — compounds until incident | Detected — automated Drift-Patch-Seal |
| Leadership discontinuity | Damaging — new leaders lack decision context | Mitigated — sealed episodes preserve rationale |
| Reputation risk | Latent — stale claims presented as current | Managed — TTL discipline enforces freshness |

One avoided failure offsets years of cost.

### Relationship to Existing Economic Analysis

This model extends the conceptual framework in:

- [Economic Tension](../../category/economic_tension.md) — failure mode language and cost framing
- [Risk Model](../../category/risk_model.md) — decision entropy, assumption half-life, drift accumulation curve

The Credibility Engine adds concrete cost-per-node metrics and scale-specific budget ranges to those conceptual models.

---

## Guardrails

All deployment patterns, budgets, and team sizes are abstract models for institutional planning. Not specific to any domain, industry, or organization. No proprietary data or market statistics.
