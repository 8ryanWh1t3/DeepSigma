# LLM Data Model — One-Pager

## What is it?

The LLM Data Model is a **canonical record envelope** that wraps every piece of data your AI systems touch.  It ensures that every fact, decision, document, event, and entity carries its own provenance, freshness rules, confidence score, and cryptographic seal.

Think of it as the "passport" every data object must carry before an LLM or agent is allowed to reason over it.

## Why does it matter?

Traditional data models assume a human will interpret context.  AI systems don't have that luxury.  They need:

- **Truth** — Where did this data come from?  Who observed it?  What evidence backs it?
- **Reasoning** — What decisions were made using this data?  What was the confidence?
- **Memory** — How do we retrieve this data later?  How do we know it hasn't expired?

Without these properties, LLMs hallucinate, agents act on stale data, and auditors can't trace what happened.

## The envelope

Every record in the data model is wrapped in a **Canonical Record Envelope** containing:

- **Identity**: `record_id` (UUID) + `record_type`
- **Timestamps**: `created_at`, `observed_at`
- **Provenance**: `source` → `provenance` chain (Claim → Evidence → Source)
- **Confidence**: 0–1 score with explanation
- **Freshness**: `ttl` (time-to-live) + `assumption_half_life`
- **Classification**: `labels` (domain, sensitivity, project)
- **Graph edges**: `links` (supports, contradicts, derived_from, etc.)
- **Payload**: `content` (type-specific data)
- **Integrity**: `seal` (hash + signature + version + patch_log)

## Record types

| Type | What it captures | Example |
|---|---|---|
| `Claim` | An assertion with evidence and confidence | "Account X is compromised" (confidence: 0.87) |
| `DecisionEpisode` | A sealed, immutable decision record | Agent quarantined account X within 200ms |
| `Document` | A policy, DTE, or reference document | Policy Pack v2.1 for AccountQuarantine |
| `Event` | Something that happened at a point in time | Drift detected: TTL breach on feature Y |
| `Entity` | A persistent object in the domain | Customer record, service endpoint, model version |
| `Metric` | A measured value with timestamp | P99 latency = 160ms for decision type Z |

## How it connects to Σ OVERWATCH

The LLM Data Model is the **persistence and retrieval layer** underneath the RAL runtime:

```
  Agent / LLM
       │
  ┌────▼─────┐
  │ RAL      │  ← runtime: DTEs, action contracts, verification
  │ (specs/) │
  └────┬─────┘
       │
  ┌────▼──────────┐
  │ LLM Data     │  ← persistence: canonical records, provenance, seals
  │ Model        │
  └────┬──────────┘
       │
  ┌────▼──────────┐
  │ Coherence    │  ← governance: DLR, RS, DS, MG
  │ Ops          │
  └──────────────┘
```

## Who uses it?

- **Agents** — query records via vector + keyword + graph retrieval
- **Supervisors** — validate provenance and freshness before allowing actions
- **Auditors** — trace any decision back to its evidence chain
- **Drift detectors** — compare expected vs. actual using sealed records
- **Coherence Ops** — align DLR/RS/DS/MG artifacts to canonical records
