# 19 — Claim: Universal Atomic Primitive

> **Schema**: [`specs/claim.schema.json`](../specs/claim.schema.json)
> > **Example**: [`llm_data_model/03_examples/claim_primitive_example.json`](../llm_data_model/03_examples/claim_primitive_example.json)
> > > **Version**: 1.0.0
> > > > **Status**: Active
> > > >
> > > > ---
> > > >
> > > > ## What is a Claim?
> > > >
> > > > A **Claim** is the indivisible unit of asserted truth in the Overwatch ecosystem. It is the atomic substrate from which every higher-order structure is composed:
> > > >
> > > > | Structure | Composition |
> > > > |---|---|
> > > > | **DLR** (Decision Log Record) | List of `claimId`s + rationale graph |
> > > > | **Canon** (Blessed Memory) | `claimId`s promoted to external memory |
> > > > | **Drift / Retcon / Patch** | Operations on claim versions |
> > > > | **Reflection Session** | Claims aggregated into learning summaries |
> > > > | **IRIS Query** | Resolved against claim provenance chains |
> > > >
> > > > A Claim is **not** a generic record. It is a first-class schema with enforced fields, typed epistemic categories, built-in decay semantics, and a native graph for lineage tracking.
> > > >
> > > > ---
> > > >
> > > > ## Why a dedicated schema?
> > > >
> > > > The existing `canonical_record.schema.json` in `llm_data_model/` provides a generic envelope where `record_type: "Claim"` stores claim-specific data in an unvalidated `content` object. This works for storage but does not enforce the structural invariants that make claims composable, auditable, and machine-comparable.
> > > >
> > > > `specs/claim.schema.json` is a **standalone first-class spec** at the same level as DTE, Action Contract, Episode, and Drift. It enforces:
> > > >
> > > > - **Testable statement** as a required top-level field (not buried in provenance)
> > > > - - **Epistemic typing** (`truthType`) so systems know *how* to trust a claim
> > > >   - - **Scoping** (where + when + context) so claims have bounded applicability
> > > >     - - **Status light** derivation for immediate triage
> > > >       - - **Half-life with computed expiry** so claims decay on schedule
> > > >         - - **Named claim-graph edges** (not generic links) for lineage
> > > >           - - **Provenance chain with roles** for full trust lineage
> > > >             - - **Classification** for access control
> > > >              
> > > >               - ---
> > > >
> > > > ## Required Fields
> > > >
> > > > Every Claim **must** have:
> > > >
> > > > | Field | Type | Purpose |
> > > > |---|---|---|
> > > > | `claimId` | `CLAIM-YYYY-NNNN` | Stable domain-level identifier. Never reused. |
> > > > | `statement` | string (min 10 chars) | One sentence, testable assertion. |
> > > > | `scope` | object | Where and when this claim applies. |
> > > > | `truthType` | enum | Epistemic category of the claim. |
> > > > | `confidence` | object | Score (0.00–1.00) + explanation. |
> > > > | `statusLight` | enum | Derived traffic light (green/yellow/red). |
> > > > | `sources` | array (min 1) | Pointers to source material. |
> > > > | `evidence` | array | Artifacts supporting the claim. |
> > > > | `owner` | string | Accountable role or function. |
> > > > | `timestampCreated` | date-time | When the claim was first asserted. |
> > > > | `version` | semver | Semantic version (e.g., 1.0.0). |
> > > > | `halfLife` | object | Validity window + expiry + refresh trigger. |
> > > > | `seal` | object | Immutable hash + version + patch log. |
> > > >
> > > > ---
> > > >
> > > > ## Truth Types
> > > >
> > > > The `truthType` field classifies the epistemic basis of the claim:
> > > >
> > > > | Value | Meaning | Example |
> > > > |---|---|---|
> > > > | `observation` | Directly measured or witnessed | Sensor reading, log entry |
> > > > | `inference` | Derived from evidence via reasoning | Pattern correlation result |
> > > > | `assumption` | Taken as given without direct evidence | Baseline configuration |
> > > > | `forecast` | Predictive, based on models or trends | Projected load curve |
> > > > | `norm` | Policy, standard, or organizational rule | SLA threshold |
> > > > | `constraint` | Hard boundary that cannot be violated | Regulatory limit |
> > > >
> > > > ---
> > > >
> > > > ## Status Light Derivation
> > > >
> > > > The `statusLight` field is derived from `confidence.score` and source quality:
> > > >
> > > > | Light | Condition |
> > > > |---|---|
> > > > | **green** | `confidence.score >= 0.80` AND at least 1 source with `reliability: "high"` |
> > > > | **yellow** | `confidence.score` between 0.50–0.79 OR sources are mixed reliability |
> > > > | **red** | `confidence.score < 0.50` OR unresolved contradiction exists in `graph.contradicts` |
> > > >
> > > > These thresholds are defaults. Policy packs can override them per decision type.
> > > >
> > > > ---
> > > >
> > > > ## Half-Life and Decay
> > > >
> > > > Claims are not eternal. The `halfLife` object controls temporal validity:
> > > >
> > > > - `value` + `unit`: How long before confidence should be halved (hours, days, or ms)
> > > > - - `expiresAt`: Computed timestamp (timestampCreated + halfLife)
> > > >   - - `refreshTrigger`: What forces re-evaluation — `expiry`, `contradiction`, `new_source`, `schedule`, or free-text
> > > >    
> > > >     - A claim with `halfLife.value: 0` is **perpetual** (e.g., immutable constraints).
> > > >    
> > > >     - When a claim expires, the system should either refresh it (new version via `supersedes`) or degrade it (statusLight drops toward red).
> > > >    
> > > >     - ---
> > > >
> > > > ## Claim Graph
> > > >
> > > > The `graph` object provides typed edges to other claims:
> > > >
> > > > | Edge | Meaning |
> > > > |---|---|
> > > > | `dependsOn[]` | This claim requires these claims to be true |
> > > > | `contradicts[]` | These claims are in active conflict |
> > > > | `supersedes` | This claim replaces a prior claim (never overwrite) |
> > > > | `patches[]` | Patch IDs that modified meaning or confidence |
> > > > | `supports[]` | This claim provides evidence for these claims |
> > > >
> > > > This creates a directed graph where every claim knows its lineage, conflicts, and dependencies. DLR becomes a subgraph query. Canon becomes a blessing operation on graph nodes. Drift becomes an edge-weight change.
> > > >
> > > > ---
> > > >
> > > > ## Provenance Chain
> > > >
> > > > The `provenanceChain` array records the ordered trust lineage:
> > > >
> > > > ```
> > > > Claim -> Evidence -> Source
> > > > ```
> > > >
> > > > Each entry has a `type` (claim/evidence/source), a `ref` (pointer), and a `role` describing its function in the chain (e.g., `root_assertion`, `primary_evidence`, `corroborating_source`).
> > > >
> > > > This is distinct from the generic `provenance.chain` in the canonical record envelope. The claim provenance chain is typed, role-annotated, and designed for IRIS query resolution.
> > > >
> > > > ---
> > > >
> > > > ## Relationship to Existing Schemas
> > > >
> > > > | Existing Schema | Relationship to Claim |
> > > > |---|---|
> > > > | `canonical_record.schema.json` | Claim is a **specialization**. Claims can be wrapped in the canonical envelope for storage (record_type: "Claim"), but the claim schema enforces richer structure. |
> > > > | `episode.schema.json` | Episodes **contain** claims. The `context.evidenceRefs` can point to claimIds. |
> > > > | `drift.schema.json` | Drift events **operate on** claims. A drift event may reference claim version changes. |
> > > > | `action_contract.schema.json` | Action contracts may **require** claims as preconditions. |
> > > > | `dte.schema.json` | DTEs govern the **timing** of claim-producing decisions. |
> > > >
> > > > ---
> > > >
> > > > ## Bridge: Canonical Record to Claim Primitive
> > > >
> > > > To convert an existing `record_type: "Claim"` canonical record to the Claim Primitive:
> > > >
> > > > | Canonical Record Field | Claim Primitive Field |
> > > > |---|---|
> > > > | `record_id` | `claimId` (new format: CLAIM-YYYY-NNNN) |
> > > > | `provenance.chain[0].statement` | `statement` (promoted to top-level) |
> > > > | *(missing)* | `scope` (new) |
> > > > | *(missing)* | `truthType` (new) |
> > > > | `confidence.score` | `confidence.score` (same) |
> > > > | *(missing)* | `statusLight` (new, derived) |
> > > > | `provenance.chain` (type=source) | `sources[]` (restructured) |
> > > > | `provenance.chain` (type=evidence) | `evidence[]` (restructured) |
> > > > | *(missing)* | `owner` (new) |
> > > > | `created_at` | `timestampCreated` (renamed) |
> > > > | `observed_at` | `timestampObserved` (renamed) |
> > > > | `seal.version` | `version` (promoted to semver string) |
> > > > | `assumption_half_life` (ms) | `halfLife` (object with value + unit + expiresAt + refreshTrigger) |
> > > > | `links[]` | `graph` (restructured into named typed edges) |
> > > > | `provenance.chain` | `provenanceChain` (with roles) |
> > > > | `labels.sensitivity` | `classificationTag` (renamed) |
> > > > | `seal` | `seal` (same structure, camelCase) |
> > > >
> > > > ---
> > > >
> > > > ## Composability Payoff
> > > >
> > > > Once Claims exist as first-class primitives, every downstream operation simplifies:
> > > >
> > > > - **DLR** = query the claim graph for a decision's claim subgraph + rationale
> > > > - - **Canon** = bless specific claimIds for promotion to long-term memory
> > > >   - - **Drift** = detect when claim confidence decays, contradictions emerge, or half-lives expire
> > > >     - - **Retcon** = supersede a claim with a corrected version, preserving the original via `supersedes`
> > > >       - - **Patch** = append to `seal.patchLog` without breaking the immutable seal
> > > >         - - **IRIS** = resolve WHY/WHAT_CHANGED/WHAT_DRIFTED by walking provenance chains
> > > >          
> > > >           - ---
> > > >
> > > > ## Files
> > > >
> > > > | File | Path |
> > > > |---|---|
> > > > | JSON Schema | `specs/claim.schema.json` |
> > > > | Worked Example | `llm_data_model/03_examples/claim_primitive_example.json` |
> > > > | This Document | `docs/19-claim-primitive.md` |
