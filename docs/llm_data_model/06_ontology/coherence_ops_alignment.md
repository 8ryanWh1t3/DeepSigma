# Coherence Ops Alignment

How the LLM Data Model maps to the four Coherence Ops artifacts: DLR, RS, DS, and MG.

## Artifact-to-record mapping

| Coherence Ops artifact | Canonical record type | Mapping description |
|---|---|---|
| **DLR** (Decision Log Record) | `DecisionEpisode` | Each DLR entry maps 1:1 to a sealed DecisionEpisode record.  The DLR is the log; the canonical record is the storage. |
| **RS** (Reflection Session) | `Claim` | RS summaries are Claims about system behavior — divergences, insights, recommendations.  Each RS produces one or more Claim records. |
| **DS** (Drift Signal) | `Event` | Drift signals are Events with `labels.domain = "drift"`.  The DS collector aggregates these into DriftSummary records (also Events). |
| **MG** (Memory Graph) | Graph of all record types | The MG is the graph formed by `links[]` edges across all canonical records.  MG nodes = canonical records; MG edges = `links[].rel` values. |

## Detailed field alignment

### DLR → DecisionEpisode

| DLR field | Canonical field | Notes |
|---|---|---|
| `episode_id` | `content.episode_id` | Business key inside the content payload |
| `decision_type` | `content.decision_type` | The DTE type that governed the decision |
| `actor` | `content.actor` | Who/what made the decision |
| `timestamp` | `observed_at` | When the decision was observed |
| `outcome` | `content.outcome.code` | success, partial, fail, abstain, bypassed |
| `telemetry` | `content.telemetry` | Full telemetry block |
| `policy_ref` | `content.dte_ref.policy_pack_hash` | Policy that governed the decision |

### RS → Claim

| RS field | Canonical field | Notes |
|---|---|---|
| `session_id` | `record_id` | UUID for the reflection session output |
| `divergences[]` | Multiple `Claim` records | Each divergence becomes a separate Claim with `labels.tags = ["reflection", "divergence"]` |
| `summary` | `content.summary` | Human-readable session summary |
| `recommendations[]` | `content.recommendations` | Actionable suggestions |
| `confidence` | `confidence.score` | How confident the RS is in its findings |

### DS → Event

| DS field | Canonical field | Notes |
|---|---|---|
| `drift_id` | `content.drift_id` | Unique drift signal identifier |
| `drift_type` | `content.drift_type` | time, freshness, fallback, bypass, verify, outcome, fanout, contention |
| `severity` | `content.severity` | green, yellow, red |
| `episode_id` | Links via `derived_from` | Edge connecting drift event to the episode that triggered it |
| `recommended_patch_type` | `content.recommended_patch_type` | dte_change, ttl_change, etc. |
| `bucket` | `labels.tags[]` | DS aggregation bucket as a tag |

### MG → Graph structure

| MG component | Canonical equivalent | Notes |
|---|---|---|
| `GraphNode` | Any canonical record | Every record is a node |
| `GraphEdge` | `links[]` entry | Every link is an edge |
| `NodeKind` | `record_type` | EPISODE, DTE, ACTION, DRIFT, POLICY, REFLECTION → map to Claim, DecisionEpisode, Event, Document, Entity |
| `EdgeKind` | `links[].rel` | SUPPORTS, CONTRADICTS, DERIVED_FROM, etc. |
| Weight | `confidence.score` | Implicit edge weight from source node confidence |
| Timestamp | `observed_at` | Node creation time |

## Scoring dimensions

The Coherence Ops scorer uses these canonical record fields:

| Dimension | Weight | Source fields |
|---|---|---|
| Completeness | 0.25 | Count of required envelope fields present across all records |
| Consistency | 0.25 | Cross-record link integrity — all `links[].target` resolve to existing records |
| Freshness | 0.20 | Proportion of records not expired (`observed_at + ttl > now`) |
| Provenance | 0.15 | Proportion of records with ≥ 2 provenance chain entries |
| Traceability | 0.15 | Proportion of DecisionEpisodes with at least one `derived_from` link |

## Integration pattern

```
Canonical Store
     │
     ├── DLR reads DecisionEpisode records
     ├── RS writes Claim records (divergences)
     ├── DS writes Event records (drift signals)
     └── MG traverses links[] across all records
```
