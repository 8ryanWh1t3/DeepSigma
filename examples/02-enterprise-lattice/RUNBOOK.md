---
title: "Enterprise Lattice — Operational Runbook"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# Enterprise Lattice Runbook

> Semi-automated governance for ~500 nodes across 3 domains.

---

## Operational Profile

| Parameter | Value |
|-----------|-------|
| Scale | ~500 nodes |
| Domains | 3 (Alpha, Beta, Gamma) |
| Sources | 25 across 6 correlation groups |
| Sync Planes | 3 (one per domain), 2 beacons each |
| Drift detection cadence | 15-minute cycle |
| Patch approval | Automated below yellow; human DRI for yellow/red |
| Team | 6–8 engineers |
| Budget | $1.5M–$3M/year |

---

## Daily Operations

### Morning Check (First 15 Minutes)

1. **Review Credibility Index** — Is the composite score in expected band?
2. **Check overnight drift signals** — Any yellow or red DS artifacts?
3. **Verify Sync Plane health** — All 6 beacons reporting? Watermarks advancing?
4. **Review pending patches** — Any patches awaiting human approval?

### Continuous Monitoring

| Metric | Healthy | Warning | Action |
|--------|---------|---------|--------|
| Credibility Index | 85–100 | <85 | Review flagged claims |
| Active drift signals | 0–2 green | Any yellow | Investigate root cause |
| Sync Plane beacon lag | <100ms | >500ms | Check NTP, network |
| TTL expiration rate | <5% of evidence | >10% | Review source refresh cadence |
| Quorum margin (N−K) | ≥ 2 | = 1 | Add redundant source |

### Weekly Review

1. **Correlation risk audit** — Which sources feed the most claims? Any new cross-domain dependencies?
2. **TTL compliance** — What percentage of evidence refreshed within TTL? Trend up or down?
3. **Patch effectiveness** — Did patches resolve drift signals? Any recurring patterns?
4. **Seal integrity** — Spot-check 3 sealed episodes for hash chain validity

---

## Drift Response Playbooks

### Green Drift (Automated)

```
Trigger: Drift signal, green severity
Action:  Auto-generate DS artifact
         Auto-create patch if known pattern
         Auto-apply patch
         Auto-seal DecisionEpisode
DRI:     System (no human required)
SLA:     30 minutes detection-to-seal
```

### Yellow Drift (Semi-Automated)

```
Trigger: Drift signal, yellow severity
Action:  Auto-generate DS artifact
         Auto-create patch proposal
         Notify domain DRI
         DRI reviews and approves/modifies patch
         Apply patch
         Seal DecisionEpisode
DRI:     Domain engineer
SLA:     4 hours detection-to-seal
```

### Red Drift (Human-Led)

```
Trigger: Drift signal, red severity OR Tier 0 claim flip to UNKNOWN
Action:  Auto-generate DS artifact
         Halt automated patching
         Page on-call DRI
         Root cause analysis (mandatory)
         DRI creates patch with rollback plan
         Peer review of patch
         Apply patch
         Seal DecisionEpisode
DRI:     Senior engineer + governance lead
SLA:     8 hours detection-to-seal (24h for cross-domain)
```

---

## Cross-Domain Correlation Response

When a source feeding multiple domains drifts:

1. **Identify blast radius** — Which claims, in which domains, depend on this source?
2. **Assess correlation risk** — Are affected claims independent via other sources, or fully dependent?
3. **Coordinate across domains** — Single DRI for cross-domain events (not per-domain)
4. **Patch atomically** — All affected domains patched in one sealed episode, not piecemeal

The redundancy illusion is the primary risk at enterprise scale. Sources that appear independent may share infrastructure. The correlation group registry must be reviewed weekly.

---

## Sync Plane Operations

### Beacon Health

| Check | Cadence | Action on Failure |
|-------|---------|-------------------|
| Beacon heartbeat | Every 30s | Alert if 3 consecutive misses |
| Beacon-to-domain lag | Every 60s | Alert if >200ms sustained |
| Cross-beacon divergence | Every 5min | Alert if beacons disagree >100ms |

### Watermark Management

- Each domain Sync Plane maintains its own watermark
- Watermark stall >5 minutes triggers `SignalLoss` for the domain
- Late arrivals (below watermark) are quarantined, not rejected

### Beacon Federation

Enterprise-scale Sync Planes share beacons across domains for cross-domain time consistency. If a federated beacon fails:

1. Domains fall back to their local-only beacon
2. Cross-domain evidence ordering is flagged as provisional
3. Re-validate cross-domain claims when federation restores

---

## Quorum Emergency Procedures

### Single Source Loss

```
Impact:  1 correlation group degraded
Action:  Check quorum margins on affected claims
         If N−K ≥ 1: Monitor, no immediate action
         If N−K = 0: Claim flips to UNKNOWN (automatic)
                     Page DRI, begin source replacement
```

### Correlation Group Loss

```
Impact:  All sources in a correlation group offline
Action:  Immediate escalation to red
         Identify all claims dependent on this group
         If claims have sources in other groups: quorum may hold
         If claims are group-dependent: flip to UNKNOWN, page DRI
```

### Domain-Wide Source Failure

```
Impact:  Majority of sources in one domain offline
Action:  Quarantine entire domain
         Cross-domain claims re-evaluated without quarantined evidence
         Incident response: infrastructure team engaged
         Recovery: staged re-admission of sources with validation
```

---

## Escalation Matrix

| Condition | DRI Level | SLA |
|-----------|-----------|-----|
| Green drift, single domain | System (auto) | 30 min |
| Yellow drift, single domain | Domain engineer | 4 hours |
| Red drift, single domain | Senior engineer | 8 hours |
| Any drift, cross-domain | Governance lead | 8 hours |
| Tier 0 claim → UNKNOWN | Senior engineer + governance lead | 4 hours |
| Sync Plane failure | Infrastructure lead | 2 hours |
| Credibility Index < 70 | All DRIs + leadership | 1 hour |
