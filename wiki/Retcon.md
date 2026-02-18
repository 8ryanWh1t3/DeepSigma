# Retcon — Retroactive Claim Correction

> When the truth changes, the record must change with it — but never silently.
>
> ## Overview
>
> A **Retcon** (retroactive continuity correction) is the formal mechanism for correcting a Claim after the fact. Unlike a Patch (which adjusts confidence or metadata on an existing claim), a Retcon replaces the statement itself by creating a new superseding claim and linking it to the original.
>
> The key principle: **the original claim is never deleted or overwritten**. It remains in the graph with its full history intact. The Retcon creates a new claim, sets `graph.supersedes` to point at the original, and records the full rationale for the correction.
>
> **Schema**: [`specs/retcon.schema.json`](../specs/retcon.schema.json)
>
> ## Retcon vs Patch
>
> | Dimension | Patch | Retcon |
> |---|---|---|
> | **What changes** | Confidence, metadata, evidence | The statement itself |
> | **Original claim** | Modified in-place (via `seal.patchLog`) | Preserved — new claim created |
> | **Graph link** | `patches` edge | `supersedes` edge |
> | **Authority** | Automated or analyst | Requires explicit authorization |
> | **Blast radius** | Local | Cascading — affects dependents, canon, DLRs |
>
> ## When to Issue a Retcon
>
> | Trigger | Example |
> |---|---|
> | New evidence contradicts the original claim | Satellite imagery disproves ground report |
> | Source revealed as unreliable | Intelligence source fabricated data |
> | Methodology was flawed | Statistical model had selection bias |
> | Context changed fundamentally | Regime change invalidates political assessment |
> | Canon entry needs correction | Blessed truth discovered to be wrong |
>
> ## Anatomy of a Retcon
>
> | Field | Purpose |
> |---|---|
> | `retconId` | Stable ID (`RETCON-YYYY-NNNN`). Never reused. |
> | `originalClaimId` | The claim being retroactively corrected |
> | `newClaimId` | The replacement claim (must have `graph.supersedes` pointing back) |
> | `affectedClaimIds` | Other claims impacted (dependents in the graph) |
> | `affectedDlrIds` | DLRs whose rationale graph references the original claim |
> | `affectedCanonIds` | Canon entries that included the original claim |
> | `reason` | Full explanation of why the retcon is necessary |
> | `newEvidence` | Evidence that triggered the correction |
> | `impactAssessment` | Blast radius analysis: low/medium/high/critical |
> | `authorizedBy` | Role or authority that approved the retcon |
> | `retconAt` | When the retcon was executed |
> | `seal` | SHA-256 hash + version + sealed timestamp |
>
> ## Impact Assessment
>
> Every Retcon includes a blast-radius analysis:
>
> | Level | Meaning |
> |---|---|
> | **low** | Few or no downstream dependents affected |
> | **medium** | Some dependent claims need re-evaluation |
> | **high** | Multiple DLRs and canon entries affected |
> | **critical** | Foundational claim — cascading re-evaluation required |
>
> The assessment also tracks whether canon entries need updating (`requiresCanonUpdate`) and whether DLRs need reissue (`requiresDlrReissue`).
>
> ## Retcon Lifecycle
>
> ```
> New evidence arrives
>     |
>     v
> Original claim identified as incorrect
>     |
>     v
> New superseding claim created
>     |
>     v
> Retcon record authored
>     |
>     v
> Impact assessment computed
>     |
>     v
> Authority authorizes retcon
>     |
>     v
> Retcon sealed
>     |
>     v
> Affected artifacts updated:
>     - Dependent claims re-evaluated
>     - Canon entries flagged for review
>     - DLR rationale graphs annotated
> ```
>
> ## Relationship to Other Primitives
>
> | Primitive | Relationship |
> |---|---|
> | **Claim** | Retcon creates a new claim that supersedes the original |
> | **Canon** | Canon entries referencing retconned claims need review |
> | **DLR** | DLRs referencing retconned claims are annotated, not rewritten |
> | **IRIS** | `WHAT_CHANGED` queries surface recent retcons |
> | **Drift** | Drift detection may trigger retcon when decay crosses threshold |
> | **Seal** | Retcon records are sealed — the correction itself is immutable |
>
> ## Graph Integrity
>
> Retcon preserves full provenance. After a retcon:
>
> 1. The original claim remains in the graph (it is never deleted)
> 2. The new claim has `graph.supersedes` pointing to the original
> 3. The retcon record links both, with full audit trail
> 4. Any claim with `graph.dependsOn` referencing the original is flagged for re-evaluation
> 5. IRIS queries that walk the graph see the supersession chain
>
> This means you can always answer: "What did we believe then? What do we believe now? Why did it change?"
>
> ## Related Pages
>
> - [Unified Atomic Claims](Unified-Atomic-Claims) — the Claim Primitive that Retcon corrects
> - [Canon](Canon) — blessed claim memory that may need retcon
> - [Sealing & Episodes](Sealing-and-Episodes) — immutability model
> - [Drift to Patch](Drift-to-Patch) — the drift lifecycle (patches vs retcons)
> - [Schemas](Schemas) — all JSON Schema specs
