# Edge Types

Edges connect nodes (canonical records) in the knowledge graph via the `links[]` array.  Each edge has a `rel` (relationship type) and a `target` (the record_id of the destination node).

## Standard edge types

| Edge type | Direction | Meaning | Example |
|---|---|---|---|
| `supports` | A → B | A provides evidence for B | Claim supports Entity (this evidence backs that entity's status) |
| `contradicts` | A → B | A provides counter-evidence against B | New Claim contradicts earlier Claim |
| `derived_from` | A → B | A was computed or generated from B | Claim derived_from Event (claim was generated from a drift event) |
| `supersedes` | A → B | A replaces B (newer version) | Document v2 supersedes Document v1 |
| `part_of` | A → B | A is a component or member of B | Entity part_of Entity (account part of organization) |
| `caused_by` | A → B | A was triggered by B | Event caused_by Event (drift caused by latency spike) |
| `verified_by` | A → B | A was verified using B | DecisionEpisode verified_by Event (episode verified by read-after-write check) |

## Edge properties

Edges in the `links[]` array are lightweight — just `rel` and `target`.  For richer metadata, use the Coherence Ops Memory Graph (MG) which supports weighted, timestamped edges.

| Property | Source | Description |
|---|---|---|
| `rel` | `links[].rel` | The relationship type (see table above) |
| `target` | `links[].target` | The `record_id` of the destination node |
| Weight (implicit) | `confidence.score` of the source node | Higher-confidence sources produce stronger edges |
| Freshness (implicit) | `ttl` + `observed_at` of the source node | Expired nodes produce stale edges — excluded from traversal by default |

## Traversal rules

1. **Freshness gate** — before following an edge, check if the source node's TTL has expired.  If expired, skip the edge or mark it as stale.
2. **Confidence threshold** — traversals can specify a minimum confidence.  Edges from nodes below the threshold are excluded.
3. **Depth limit** — graph queries should specify a maximum depth to prevent unbounded traversal.
4. **Direction** — edges are directional.  `A supports B` does not imply `B supports A`.  Use explicit bidirectional links when needed.

## Common traversal patterns

| Pattern | Query | Use case |
|---|---|---|
| Evidence chain | Follow `derived_from` + `supports` backward from a Claim | Audit: trace a claim to its sources |
| Decision lineage | Follow `derived_from` from DecisionEpisode | Understand what data a decision used |
| Version history | Follow `supersedes` chain from latest Document | Show policy evolution over time |
| Impact analysis | Follow `caused_by` backward from a drift Event | Root cause analysis |
| Verification | Follow `verified_by` from a DecisionEpisode | Confirm which verification checked the decision |
| Contradiction detection | Find pairs connected by `contradicts` | Surface conflicting evidence for review |

## Mapping to Coherence Ops Memory Graph

The `links[]` edges in the canonical envelope map directly to the Memory Graph (MG) in Coherence Ops:

| Envelope edge | MG edge kind | Notes |
|---|---|---|
| `supports` | `SUPPORTS` | Direct mapping |
| `contradicts` | `CONTRADICTS` | Direct mapping |
| `derived_from` | `DERIVED_FROM` | Direct mapping |
| `supersedes` | `SUPERSEDES` | Direct mapping |
| `part_of` | `PART_OF` | Direct mapping |
| `caused_by` | `CAUSED_BY` | Direct mapping |
| `verified_by` | `VERIFIED_BY` | Direct mapping |
