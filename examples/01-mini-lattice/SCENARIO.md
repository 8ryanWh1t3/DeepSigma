---
title: "Mini Lattice — Teaching Scenario"
version: "1.0.0"
status: "Example"
last_updated: "2026-02-19"
---

# Mini Lattice Scenario

> 12 nodes. One claim. One drift. One patch. One seal.

This scenario walks through the full Drift→Patch→Seal lifecycle at minimum viable scale.

---

## Guardrails

Abstract, non-domain example. Models a high-consequence capability that must remain deployable, commandable, survivable, controlled, and externally credible — without ever being exercised. No real-world weapon modeling. Pure institutional credibility architecture.

---

## Baseline State (T₀)

The lattice is healthy. All evidence is fresh. Quorum holds.

| Node | Status | Confidence | TTL Remaining |
|------|--------|-----------|---------------|
| Claim-A | OK | — | — |
| SubClaim-A1 | OK | — | — |
| SubClaim-A2 | OK | — | — |
| SubClaim-A3 | OK | — | — |
| Evidence-E1 | OK | 0.92 | 3h 45m |
| Evidence-E2 | OK | 0.88 | 7h 10m |
| Evidence-E3 | OK | 0.95 | 3h 50m |
| Evidence-E4 | OK | 0.90 | 0h 55m |
| Evidence-E5 | OK | 0.85 | 0h 50m |

**Credibility Index: ~88** (Minor drift band)

---

## Event 1: TTL Expiration (T₁ = T₀ + 65 min)

Evidence-E4 and Evidence-E5 have 1-hour TTLs. At T₁, both expire.

### What Happens

1. `SignalLoss` event fires for E4 and E5
2. SubClaim-A3 loses both evidence sources
3. SubClaim-A3 quorum breaks (N=2, K=1, but 0 remaining)
4. `ClaimFlip` event: SubClaim-A3 → **UNKNOWN**
5. Claim-A remains OK (A1 and A2 still hold), but the Credibility Index drops

### Resulting State

| Node | Status | Change |
|------|--------|--------|
| Evidence-E4 | UNKNOWN | TTL expired |
| Evidence-E5 | UNKNOWN | TTL expired |
| SubClaim-A3 | UNKNOWN | Quorum broken |
| Claim-A | OK | Degraded (1 of 3 subclaims UNKNOWN) |

**Credibility Index: ~72** (Elevated risk)

---

## Event 2: Drift Detection (T₂ = T₁ + 1 min)

The drift detection service identifies the TTL expiration pattern.

### DS Artifact Generated

```
Drift Signal:
  category: TTL Compression
  severity: Yellow
  affected_claims: [SubClaim-A3]
  affected_evidence: [Evidence-E4, Evidence-E5]
  source: Source-S2
  root_cause: "TTL expiration without refresh — Source-S2 feed delayed"
  runtime_types: [freshness, time]
```

### DLR Entry

```
Decision: Investigate Source-S2 feed delay for SubClaim-A3 evidence
Decided_by: Drift automation (DRI: system)
Evidence: DS artifact + SignalLoss events for E4, E5
Rationale: SubClaim-A3 has zero quorum margin; TTL expiration is not a false positive
```

---

## Event 3: Patch (T₃ = T₂ + 10 min)

Source-S2 comes back online. Fresh evidence is ingested.

### Patch Object

```
Patch:
  drift_signal_ref: DS-001
  action: "Re-ingest Evidence-E4 and E5 from Source-S2 with fresh TTLs"
  rollback_plan: "Revert to UNKNOWN if new evidence confidence < 0.80"
  blast_radius: [SubClaim-A3, Claim-A]
```

### What Happens

1. `EvidenceReported` event fires for E4 (confidence: 0.91) and E5 (confidence: 0.87)
2. `PatchApplied` event fires
3. SubClaim-A3 quorum restored (N=2, K=1, margin=1)
4. `ClaimFlip` event: SubClaim-A3 → **OK**

---

## Event 4: Seal (T₄ = T₃ + 1 min)

The entire drift-patch cycle is sealed as a DecisionEpisode.

### Sealed Artifacts

| Artifact | Content |
|----------|---------|
| DLR | Decision to investigate and patch Source-S2 feed |
| RS | Reasoning: TTL expiration on short-TTL evidence, Source-S2 dependency |
| DS | Drift signal: TTL compression, yellow severity |
| MG | Memory Graph diff: TRIGGERED edge from DS to SubClaim-A3, RESOLVED_BY edge from Patch to DS |

### SealCreated Event

```
Seal:
  episode_id: EP-MINI-001
  hash_chain: [previous_seal_hash, DLR_hash, RS_hash, DS_hash, MG_hash]
  sealed_at: T₄
  version: 1
```

**Credibility Index: ~88** (Minor drift — restored to baseline)

---

## Timeline

```
T₀           T₁              T₂              T₃              T₄
│            │               │               │               │
Baseline     TTL expires     Drift detected  Patch applied   Sealed
CI: ~88      CI: ~72         DS generated    CI restoring    CI: ~88
             E4,E5→UNKNOWN   DLR created     E4,E5→OK
             A3→UNKNOWN                      A3→OK
```

---

## What This Scenario Teaches

1. **TTL expiration is not optional.** Evidence-E4 and E5 had 1-hour TTLs. The lattice respected them.
2. **UNKNOWN is honest.** SubClaim-A3 flipped to UNKNOWN rather than remaining stale OK.
3. **The loop is mechanical.** Drift→DS→DLR→Patch→Seal follows a fixed sequence.
4. **Every step produces an artifact.** Nothing is informal. Everything is sealed.
5. **The Credibility Index reflects reality.** It dropped from 88 to 72 during drift and restored after patch.
6. **Quorum matters at every scale.** Even at 12 nodes, quorum loss cascades to claim status.
