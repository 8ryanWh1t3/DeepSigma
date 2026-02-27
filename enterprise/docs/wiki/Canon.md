# Canon — Blessed Claim Memory

> Canon is the act of promoting Claims from transient decision context to long-term institutional truth.
>
> ## Overview
>
> A **Canon** entry takes one or more Claim IDs that have proven their worth through DLR decisions and elevates them to blessed status — the curated subset of claims that an organization treats as ground truth until explicitly superseded.
>
> Think of it this way: Claims are born during decisions. Most claims live and die within a single DLR. But some claims prove so reliable, so foundational, that they deserve to persist beyond the episode that created them. Canon is the ceremony that makes that happen.
>
> **Schema**: [`specs/canon.schema.json`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/schemas/core/canon.schema.json)
>
> ## When to Create a Canon Entry
>
> Canon entries are appropriate when:
>
> | Trigger | Example |
> |---|---|
> | A claim has survived multiple DLR cycles without contradiction | "Supplier X delivers within 48 hours" — confirmed across 12 decisions |
> | A policy decision has been ratified | "All SignalSource claims require ≥2 independent sources" |
> | An organizational fact needs to be centralized | "Our SLA for Tier 1 incidents is 15 minutes" |
> | A forecast has been validated by outcome | "Q4 demand will exceed 10,000 units" — confirmed by actuals |
>
> ## Anatomy of a Canon Entry
>
> | Field | Purpose |
> |---|---|
> | `canonId` | Stable ID (`CANON-YYYY-NNNN`). Never reused. |
> | `title` | Human-readable name for the blessed truth |
> | `claimIds` | Ordered list of promoted Claim IDs. First = primary. |
> | `dlrIds` | Decision records that produced these claims |
> | `blessedBy` | Role or authority that approved promotion |
> | `blessedAt` | Timestamp of the blessing ceremony |
> | `expiresAt` | When this canon entry should be reviewed for renewal |
> | `scope` | Domain + region + context boundaries |
> | `version` | Semantic version — bumped on amendment |
> | `supersedes` | Prior `canonId` this entry replaces |
> | `seal` | SHA-256 hash + version + sealed timestamp |
> | `tags` | Free-form tags for search and filtering |
>
> ## Canon Lifecycle
>
> ```
> Claim born in DLR
>     ↓
> Claim survives multiple decisions
>     ↓
> Authority blesses claim → Canon entry created
>     ↓
> Canon sealed (immutable hash)
>     ↓
>                 ┌─ Canon remains valid (ground truth)
>                 │
>                 └─ New evidence arrives
>                        ↓
>                    Retcon or supersession
>                        ↓
>                    New Canon entry (supersedes old)
> ```
>
> ## Relationship to Other Primitives
>
> | Primitive | Relationship |
> |---|---|
> | **Claim** | Canon promotes claims to long-term memory |
> | **DLR** | Canon traces back to the decisions that validated the claims |
> | **Retcon** | When a canon entry's claims are wrong, Retcon corrects them |
> | **IRIS** | `WHAT_IS_CANON` queries resolve which claims are currently blessed |
> | **Drift** | Drift detection monitors canon claims for staleness |
> | **Seal** | Canon entries are sealed — append-only, never overwritten |
>
> ## Composability
>
> In graph terms, a Canon entry is a **promotion operation**: it tags a subgraph of claims as authoritative. The `claimIds` array selects nodes; the `dlrIds` array traces provenance; the `seal` locks the selection in place.
>
> Canon entries can themselves be superseded, creating a version chain of institutional truth. The `supersedes` field links new canon to old, preserving full history.
>
> ## Related Pages
>
> - [Unified Atomic Claims](Unified-Atomic-Claims) — the Claim Primitive that Canon promotes
> - [Retcon](Retcon) — retroactive correction of canon entries
> - [Sealing & Episodes](Sealing-and-Episodes) — immutability model
> - [Schemas](Schemas) — all JSON Schema specs
> - [IRIS](IRIS) — query resolution engine
