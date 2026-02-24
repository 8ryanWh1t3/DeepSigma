---
title: "Enterprise Lattice — Scenario Plan"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# Enterprise Lattice Scenario Plan

> ~500 nodes. Redundancy illusion becomes visible.

This scenario plan walks through three drift events at enterprise scale, demonstrating how correlation risk, quorum margin compression, and sync plane divergence compound in ways that are invisible at mini scale.

---

## Guardrails

Abstract, non-domain example. Models multi-domain institutional credibility across three decision domains. No real-world industry. Pure institutional credibility architecture.

---

## Lattice Recap

```
Domain Alpha: 3 claims (A1 Tier 0, A2 Tier 0, A3 Tier 1) — 27 evidence nodes
Domain Beta:  3 claims (B1 Tier 0, B2 Tier 1, B3 Tier 1) — 28 evidence nodes
Domain Gamma: 2 claims (G1 Tier 0, G2 Tier 1) — 17 evidence nodes

25 sources across 6 correlation groups
3 domain-level Sync Planes, 2 beacons each
```

**Baseline Credibility Index: ~85** (Minor drift)

The primary risk at baseline is Source-S003, which feeds 12 claims across Domain Alpha and Domain Beta.

---

## Scenario 1: Timing Entropy in Domain Beta (T₀ + 2h)

### Trigger

Domain Beta's primary evidence feed develops variable ingestion lag. The Sync Plane detects that `ingest_time - event_time` variance has increased 40% over the past 6 hours.

### Detection

| Signal | Value |
|--------|-------|
| Category | Timing entropy |
| Runtime types | time, contention |
| Severity | Yellow |
| Affected claims | B1, B2, B3 (all Beta) |
| Affected evidence | 14 nodes with ingestion lag > 2× baseline |

### Response

1. **DS artifact** — Timing entropy, yellow, 14 evidence nodes in Beta
2. **Root cause** — Beta's event stream consumer is experiencing GC pauses from memory pressure
3. **Patch** — Increase consumer heap allocation, temporarily extend Beta TTLs to absorb backlog
4. **MG update** — DriftSignal node linked to all 14 evidence nodes, Patch node with rollback (revert TTL extension after consumer stabilizes)
5. **Seal** — DecisionEpisode sealed with DLR, RS, DS, MG

### Credibility Index Impact

| Phase | Score | Band |
|-------|-------|------|
| Before | 85 | Minor drift |
| During drift | 78 | Elevated risk |
| After patch | 84 | Minor drift |

Not fully restored — the TTL extension reduces freshness guarantees temporarily.

---

## Scenario 2: Confidence Volatility on Source-S003 (T₀ + 8h)

### Trigger

Source-S003 — the cross-domain source feeding 12 claims in Alpha and Beta — begins producing confidence scores that fluctuate between 0.65 and 0.92 over 4 hours with no known external cause.

### Detection

| Signal | Value |
|--------|-------|
| Category | Confidence volatility |
| Runtime types | verify, outcome |
| Severity | Red |
| Affected claims | 12 claims across Alpha and Beta |
| Correlation risk | Maximum — single source, cross-domain |

### Response

1. **DS artifact** — Confidence volatility, red, 12 claims, cross-domain correlation risk flagged
2. **Root cause** — S003's upstream data pipeline has a schema change that intermittently corrupts confidence scoring
3. **DRI assignment** — Escalated to human DRI (red severity + cross-domain + Tier 0 claims affected)
4. **Patch** — Downgrade S003 to Tier 2 (from Tier 1), increase quorum requirement for affected claims, activate backup source S018 for Alpha
5. **MG update** — S003 tier change, new edges from S018 to Alpha claims, DriftSignal linked to all 12 affected claims
6. **Seal** — DecisionEpisode sealed

### Credibility Index Impact

| Phase | Score | Band |
|-------|-------|------|
| Before | 84 | Minor drift |
| During drift | 68 | Structural degradation |
| After patch | 80 | Elevated risk |

The correlation risk penalty from S003 is reduced by the tier downgrade and backup activation, but structural risk remains until S003's upstream pipeline is fixed.

### Key Insight

**This is the redundancy illusion.** Alpha and Beta appeared independent. They were not. A single source failure cascaded across domain boundaries because S003 was shared infrastructure.

---

## Scenario 3: External Mismatch in Domain Gamma (T₀ + 14h)

### Trigger

Beacon-B2 (external authority for Gamma) reports timestamps that diverge from Gamma's internal Sync Plane by >500ms consistently over 30 minutes.

### Detection

| Signal | Value |
|--------|-------|
| Category | External mismatch |
| Runtime types | bypass, verify |
| Severity | Yellow |
| Affected claims | G1, G2 (all Gamma) |
| Sync plane impact | Gamma evidence ordering may be unreliable |

### Response

1. **DS artifact** — External mismatch, yellow, Gamma Sync Plane divergence
2. **Root cause** — Gamma's internal NTP configuration drifted after a firewall rule change blocked the secondary NTP server
3. **Patch** — Quarantine Gamma evidence pending NTP resynchronization, restore firewall rule, validate Gamma watermarks after resync
4. **MG update** — Quarantine status on all Gamma evidence, DriftSignal linked to Sync Plane
5. **Seal** — DecisionEpisode sealed

### Credibility Index Impact

| Phase | Score | Band |
|-------|-------|------|
| Before | 80 | Elevated risk |
| During drift | 73 | Elevated risk |
| After patch | 82 | Elevated risk |

Gamma's contribution to the composite score is limited by its node count (17 of ~72 evidence nodes), but the quarantine period introduces an ongoing TTL penalty until evidence is re-validated.

---

## Cumulative Timeline

```
T₀+0h     T₀+2h       T₀+8h       T₀+14h      T₀+16h
│          │            │            │            │
Baseline   Beta timing  S003 conf.   Gamma sync   Stabilized
CI: 85     CI: 78→84    CI: 84→68→80 CI: 80→73→82 CI: ~82
```

After all three scenarios, the Credibility Index settles at ~82 (Elevated risk). The institution has three open items:

1. Beta TTL extension still active (temporary measure)
2. S003 upstream pipeline requires permanent fix
3. Gamma NTP monitoring needs hardening

---

## What This Scenario Plan Teaches

1. **Drift compounds.** Three independent drift events in 14 hours dropped the index from 85 to 68 at worst.
2. **Cross-domain correlation is the dominant risk.** Scenario 2 (S003) caused more damage than the other two combined.
3. **The Sync Plane catches infrastructure drift.** Scenario 3 would have been invisible without beacon comparison.
4. **Not all patches fully restore.** Temporary mitigations (TTL extension, tier downgrade) reduce risk without eliminating it.
5. **Each scenario produces a sealed episode.** Three drift events = three DecisionEpisodes = full audit trail.
