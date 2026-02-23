# Interop Drift Triggers

**Version:** 0.1.0
**Target Release:** v0.6.1

Drift triggers for the Coherence Ops Interop Gateway. Each row maps a drift type to its detection signal, threshold, blast radius, response action, and emitted artifact.

---

## Drift Trigger Table

| Drift Type | Detector | Signal | Threshold | Blast Radius | Severity | Action | Artifact Emitted |
|------------|----------|--------|-----------|--------------|----------|--------|------------------|
| **Schema Drift** | Response validator | Response fields don't match contract's `message_types[].schema` | Any required field missing or type mismatch | Single contract | Medium | Auto-renegotiate: generate new contract version with updated schema | DS (drift event) → Patch (field mapping) → DLR (new contract sealed) |
| **Schema Drift (additive)** | Schema diff engine | New optional fields appear in response | New fields detected | Single contract | Low | Log + update contract schema (non-breaking) | DS (drift event, informational) |
| **Semantic Drift** | Coherence scorer | Field values present but meaning changed (e.g., status code renumbered, units changed) | Coherence score drop > 10 points from baseline | Contract + all downstream consumers | High | Block traffic + require human approval — semantic changes can silently corrupt decisions | DS → escalation DLR (human approval required) → Patch → MG update |
| **Capability Drift** | Agent Card watcher / tool manifest diff | Peer's published capabilities changed (tools added, removed, or modified) | Any capability referenced by contract is removed or renamed | All contracts with affected peer | Medium | Auto-renegotiate if additions only; require human approval if removals | DS → Patch (updated capability mapping) → DLR |
| **Capability Drift (removal)** | Agent Card watcher | Capability used by active contract removed from peer's manifest | Capability in contract's `intents[].triggers` no longer available | All contracts using removed capability | Critical | Circuit break + escalate — contract cannot function | DS → incident DLR → MG (contract marked invalid) |
| **Policy Drift** | Auth probe / policy gate diff | Access control, rate limits, or auth requirements changed | Auth failure on previously authorized call, or rate limit reduced > 50% | All contracts with affected peer | High | Require human approval — policy changes affect security posture | DS → escalation DLR → Patch (updated constraints) → MG |
| **Performance Drift** | Latency / error rate monitor | Response latency or error rate exceeds contract's SLO | Latency > 2× p95 baseline for 5 consecutive calls, or error rate > 10% over 5min window | Single contract | Medium | Auto-retry with backoff → degrade ladder (L1 → L2) → circuit break at L3 | DS (performance event) → Patch (adjusted timeout/retry) |
| **Performance Drift (sustained)** | SLO breach counter | Performance SLO breached for > 15 minutes | 15-minute sustained breach | Single contract + dependent workflows | High | Circuit break + require human approval for remediation | DS → incident DLR → MG (contract marked degraded) |
| **Freshness Drift** | Contract TTL monitor | Contract `expiry` timestamp approaching or passed | Warning at 80% of TTL; critical at 100% | Single contract | Medium (80%) / High (100%) | At 80%: trigger proactive renegotiation. At 100%: block + renegotiate | DS → Patch (renewed contract) → DLR (new seal) |
| **Negotiation Drift** | Round counter / timeout | Renegotiation fails to converge | > 3 rounds or > 60s total negotiation time | Contract being renegotiated | High | Fall back to previous contract version; escalate if no rollback target | DS → rollback DLR → MG (previous version reactivated) |

---

## Severity Definitions

| Severity | Meaning | Automated Response | Human Required |
|----------|---------|-------------------|----------------|
| **Low** | Informational change; no functional impact | Log + optional schema update | No |
| **Medium** | Functional change; auto-recovery possible | Auto-renegotiate or auto-patch | No (but notified) |
| **High** | Significant change; risk of silent corruption | Block traffic + escalate | Yes — must approve patch |
| **Critical** | Contract cannot function; immediate breakage | Circuit break + incident | Yes — must approve remediation |

---

## Detection Cadence

| Detector | Frequency | Mechanism |
|----------|-----------|-----------|
| Response validator | Every call | Inline validation against contract schema |
| Schema diff engine | Every call (cached) | Hash comparison of response schema vs contract |
| Coherence scorer | Every 10 calls or 5 minutes | Batch scoring of recent interactions |
| Agent Card watcher | Every 5 minutes | Poll peer's Agent Card endpoint; diff against cached |
| Tool manifest diff | On first call after cache expiry (5min) | `tools/list` comparison |
| Auth probe | On auth failure | Reactive — triggered by 401/403 response |
| Latency monitor | Every call | Running p95 over sliding 5-minute window |
| Error rate monitor | Continuous | Sliding 5-minute window counter |
| Contract TTL monitor | Every minute | Check `expiry` field against current time |

---

## Artifact Flow

```
Drift Signal
  ↓
DeltaDriftDetector.classify(signal)
  ↓
DriftEvent {
  type: "schema" | "semantic" | "capability" | "policy" | "performance" | "freshness",
  severity: "low" | "medium" | "high" | "critical",
  contract_id: "...",
  evidence: { baseline: {...}, observed: {...}, diff: {...} }
}
  ↓
[severity=low]     → DS entry (informational)
[severity=medium]  → DS entry → auto-Patch → DLR (sealed) → MG update
[severity=high]    → DS entry → escalation queue → human approval → Patch → DLR → MG
[severity=critical]→ DS entry → circuit break → incident DLR → MG (contract invalidated)
  ↓
Coherence score recomputed after every Patch
```

---

## Integration with Existing Drift System

The interop drift triggers extend Σ OVERWATCH's existing `DeltaDriftDetector` (from Golden Path). The same artifact flow applies:

- Drift events conform to `specs/drift.schema.json`
- Patches conform to `specs/retcon.schema.json`
- All artifacts sealed with SHA-256 hash + timestamp
- Memory Graph updated with new contract versions and drift history
- IRIS queries (`WHAT_DRIFTED`, `WHY`, `STATUS`) work on interop drift events
