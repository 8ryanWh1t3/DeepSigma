# IRIS — Interface for Resolution, Insight, and Status

> The operator-facing query layer for Coherence Ops.
> > IRIS answers "why did we decide X?", "what's drifting?", and "how healthy are we?"
> > > with structured responses, full provenance chains, and sub-60-second resolution targets.
> > >
> > > ---
> > >
> > > ## 1) What IRIS Is
> > >
> > > IRIS is the **read-only query resolution engine** that sits on top of PRIME and queries against the four canonical Coherence Ops artifacts — DLR, RS, DS, and MG — to answer operator questions with full decision lineage.
> > >
> > > PRIME is the governance gate that converts LLM probability gradients into decision-grade actions (see [GLOSSARY.md](../GLOSSARY.md): "LLM proposes. PRIME disposes."). IRIS is the **terminal through which operators interact with PRIME** — the interface that makes the sealed, scored, and governed data human-accessible.
> > >
> > > ```text
> > > Operator
> > >   │
> > >   ▼
> > > ┌─────────────────────────────────────────────┐
> > > │  IRIS  (query resolution)                   │
> > > │  WHY · WHAT_CHANGED · WHAT_DRIFTED          │
> > > │  RECALL · STATUS                            │
> > > ├─────────────────────────────────────────────┤
> > > │  PRIME  (threshold gate / governance)       │
> > > │  Truth–Reasoning–Memory invariants          │
> > > ├─────────────────────────────────────────────┤
> > > │  DLR  │  RS  │  DS  │  MG                  │
> > > │  policy  outcomes  drift  provenance        │
> > > └─────────────────────────────────────────────┘
> > > ```
> > >
> > > IRIS never mutates DLR, RS, DS, or MG state. It assembles answers from their current contents and returns structured responses with provenance chains that trace every data point back to its source artifact.
> > >
> > > ---
> > >
> > > ## 2) Design Principles
> > >
> > > | Principle | Rationale |
> > > |-----------|-----------|
> > > | **Read-only** | IRIS queries artifacts but never writes to them. Mutation flows through PRIME and the runtime pipeline. |
> > > | **Provenance-first** | Every response includes a `provenance_chain` linking back to specific artifact records. No answer without lineage. |
> > > | **Sub-60-second target** | Matches the Memory Graph's institutional memory promise: "60 seconds or it doesn't exist" (see [GLOSSARY.md](../GLOSSARY.md)). |
> > > | **Structured output** | Responses are machine-parseable (JSON-serialisable) and human-readable. No unstructured prose. |
> > > | **Graceful degradation** | If an artifact is unavailable, IRIS returns a `PARTIAL` or `NOT_FOUND` status with reduced confidence rather than failing. |
> > >
> > > ---
> > >
> > > ## 3) Query Types
> > >
> > > IRIS supports five query types. Each maps to a specific operator question and resolves against specific artifacts.
> > >
> > > ### WHY — "Why did we decide X?"
> > >
> > > Resolves against **MG** (primary) and **DLR** (context).
> > >
> > > The operator provides an `episode_id`. IRIS queries the Memory Graph for the episode's provenance node — evidence references, actions, and linked drift events — then enriches with the DLR entry for policy context (decision type, outcome code, policy stamp, degrade step). The Reflection Session provides broader context when available.
> > >
> > > | Field | Source | Description |
> > > |-------|--------|-------------|
> > > | `mg_provenance` | MG | Node label, evidence refs, actions |
> > > | `dlr_entry` | DLR | Decision type, outcome, policy stamp, degrade step |
> > > | `mg_drift` | MG | Drift events linked to the episode |
> > >
> > > Confidence builds additively: MG node found (+0.4), drift context present (+0.1), DLR entry found (+0.3), RS session available (+0.1). A WHY query with all artifacts resolves at ~0.9 confidence.
> > >
> > > ### WHAT_CHANGED — "What changed?"
> > >
> > > Resolves against **DLR** (primary), **MG** (patches), and **DS** (drift summary).
> > >
> > > IRIS analyses all DLR entries within the requested time window: outcome distribution, episodes with active degrade steps, episodes missing policy stamps. MG enriches with patch counts. DS enriches with drift signal totals and severity breakdown.
> > >
> > > | Field | Source | Description |
> > > |-------|--------|-------------|
> > > | `total_entries` | DLR | Number of DLR entries analysed |
> > > | `outcome_distribution` | DLR | Count per outcome code (COMMIT, ROLLBACK, DEGRADE, ABSTAIN) |
> > > | `degraded_episodes` | DLR | Episode IDs with active degrade steps |
> > > | `policy_missing` | DLR | Episode IDs without policy stamps |
> > > | `patch_count` | MG | Number of patch nodes |
> > > | `drift_summary` | DS | Total signals, severity breakdown |
> > >
> > > ### WHAT_DRIFTED — "What's drifting?"
> > >
> > > Resolves against **DS** (primary) and **MG** (resolution status).
> > >
> > > IRIS pulls the drift summary from the Drift Scan: total signals, severity breakdown (red/yellow/green), top fingerprint buckets, and recurring patterns. MG cross-references drift nodes against patch nodes to compute a resolution ratio — what percentage of detected drifts have been patched.
> > >
> > > | Field | Source | Description |
> > > |-------|--------|-------------|
> > > | `total_signals` | DS | Total drift signals detected |
> > > | `by_type` | DS | Signal count per drift type (time, freshness, fallback, bypass, verify, outcome) |
> > > | `by_severity` | DS | Signal count per severity (red, yellow, green) |
> > > | `top_buckets` | DS | Top drift fingerprints by count |
> > > | `top_recurring` | DS | Most frequently recurring patterns |
> > > | `resolution_ratio` | MG | Patch nodes / drift nodes |
> > >
> > > ### RECALL — "What do we know about X?"
> > >
> > > Resolves against **MG** (primary) and **DLR** (enrichment).
> > >
> > > Full Memory Graph traversal for an episode: provenance node, evidence references, action nodes, drift events, and applied patches. DLR enriches with the decision type and outcome code. This is the deepest single-episode query — it returns the complete graph context for an entity.
> > >
> > > | Field | Source | Description |
> > > |-------|--------|-------------|
> > > | `provenance` | MG | Full node: label, evidence refs, actions |
> > > | `drift_events` | MG | Drift events linked to episode |
> > > | `patches` | MG | Patches applied (ID, status) |
> > > | `dlr_entry` | DLR | Decision type, outcome code |
> > >
> > > ### STATUS — "How healthy are we?"
> > >
> > > Resolves against **all four artifacts** via the Coherence Scorer.
> > >
> > > IRIS runs the `CoherenceScorer` across DLR, RS, DS, and MG to produce an overall coherence score (0–100), letter grade, and per-dimension breakdown. MG stats (node/edge counts) and a drift headline (total, red severity, recurring count) provide additional context.
> > >
> > > | Field | Source | Description |
> > > |-------|--------|-------------|
> > > | `overall_score` | CoherenceScorer | Composite 0–100 score |
> > > | `grade` | CoherenceScorer | Letter grade (A/B/C/D/F) |
> > > | `dimensions` | CoherenceScorer | Per-dimension: name, score, weight |
> > > | `mg_stats` | MG | Total nodes, total edges |
> > > | `drift_headline` | DS | Total drifts, red count, recurring count |
> > >
> > > The four scoring dimensions are: **Policy Adherence** (DLR, weight 30%), **Outcome Health** (RS, weight 25%), **Drift Control** (DS, weight 25%), and **Memory Completeness** (MG, weight 20%).
> > >
> > > ---
> > >
> > > ## 4) Response Format
> > >
> > > Every IRIS response follows the same structure, regardless of query type.
> > >
> > > ```text
> > > IRISResponse
> > > ├── query_id          (string)  — deterministic hash ID: "iris-{sha256[:12]}"
> > > ├── query_type        (enum)    — WHY | WHAT_CHANGED | WHAT_DRIFTED | RECALL | STATUS
> > > ├── status            (enum)    — RESOLVED | PARTIAL | NOT_FOUND | ERROR
> > > ├── summary           (string)  — human-readable explanation
> > > ├── data              (object)  — query-type-specific structured data (see §3)
> > > ├── provenance_chain  (array)   — ordered list of ProvenanceLink objects
> > > ├── confidence        (float)   — 0.0–1.0 estimate of answer completeness
> > > ├── resolved_at       (string)  — ISO-8601 timestamp
> > > ├── elapsed_ms        (float)   — wall-clock resolution time
> > > └── warnings          (array)   — performance or data quality warnings
> > > ```
> > >
> > > ### Provenance Chain
> > >
> > > The `provenance_chain` is an ordered list of `ProvenanceLink` objects. Each link identifies the artifact, the specific record within it, the role that record played in the answer, and an optional detail string.
> > >
> > > ```text
> > > ProvenanceLink
> > > ├── artifact   (string)  — "DLR" | "MG" | "DS" | "RS" | "PRIME"
> > > ├── ref_id     (string)  — identifier within the artifact (episode ID, DLR ID, etc.)
> > > ├── role       (string)  — "source" | "evidence" | "context"
> > > └── detail     (string)  — human-readable description of the link's contribution
> > > ```
> > >
> > > Roles follow a hierarchy: **source** is the primary artifact that produced the core answer, **evidence** provides supporting data referenced by the source, and **context** enriches the answer with additional perspective.
> > >
> > > ### Resolution Status
> > >
> > > | Status | Meaning |
> > > |--------|---------|
> > > | `RESOLVED` | Full answer assembled — confidence >= 0.5 |
> > > | `PARTIAL` | Some data found but incomplete — 0 < confidence < 0.5 |
> > > | `NOT_FOUND` | Required data missing (e.g. episode ID not found in any artifact) |
> > > | `ERROR` | Resolution failed due to an exception |
> > >
> > > ### Confidence Scoring
> > >
> > > Confidence is additive and capped at 1.0. Each artifact that contributes data to the answer adds to the confidence score. The exact weights vary by query type (see §3), but the pattern is consistent: more artifacts contributing means higher confidence.
> > >
> > > ---
> > >
> > > ## 5) IRIS and PRIME — The Governance Stack
> > >
> > > IRIS and PRIME form the two layers of the Coherence Ops governance stack. Understanding their relationship is essential.
> > >
> > > ```text
> > > ┌─────────────────────────────────────────────────────┐
> > > │                    IRIS (Phase 2)                    │
> > > │  "What happened? Why? What's drifting?"             │
> > > │  Read-only query resolution with provenance         │
> > > │  Operator-facing: natural language → structured data│
> > > ├─────────────────────────────────────────────────────┤
> > > │                    PRIME (Phase 1)                   │
> > > │  "Should we act? How? With what safeguards?"        │
> > > │  Write-path governance gate                         │
> > > │  System-facing: LLM output → decision-grade action  │
> > > ├─────────────────────────────────────────────────────┤
> > > │             DLR  /  RS  /  DS  /  MG                │
> > > │  The four canonical Coherence Ops artifacts          │
> > > └─────────────────────────────────────────────────────┘
> > > ```
> > >
> > > **PRIME** governs the **write path**: it sits between the LLM and the action layer, enforcing Truth–Reasoning–Memory invariants on every decision. PRIME converts probability gradients into sealed, policy-stamped episodes.
> > >
> > > **IRIS** governs the **read path**: it sits between the operator and the sealed artifacts, resolving questions with full provenance. IRIS never bypasses PRIME — it reads the outputs that PRIME produced.
> > >
> > > The relationship mirrors the Claim–Evidence–Source chain (see [GLOSSARY.md](../GLOSSARY.md)): PRIME enforces the chain at decision time; IRIS reconstructs it at query time.
> > >
> > > ---
> > >
> > > ## 6) Interface Contract
> > >
> > > ### Python API
> > >
> > > ```python
> > > from coherence_ops.iris import IRISEngine, IRISQuery, QueryType, IRISConfig
> > >
> > > engine = IRISEngine(
> > >     dlr_builder=dlr,
> > >     rs=reflection_session,
> > >     ds=drift_collector,
> > >     mg=memory_graph,
> > >     config=IRISConfig(
> > >         response_time_target_ms=60_000,
> > >         max_provenance_depth=50,
> > >         default_time_window_seconds=3600.0,
> > >         include_raw_artifacts=False,
> > >     ),
> > > )
> > >
> > > response = engine.resolve(IRISQuery(
> > >     query_type=QueryType.WHY,
> > >     episode_id="ep-001",
> > >     text="Why did we quarantine this account?",
> > > ))
> > >
> > > print(response.summary)
> > > print(response.confidence)
> > > for link in response.provenance_chain:
> > >     print(f"  [{link.artifact}] {link.ref_id} ({link.role}): {link.detail}")
> > > ```
> > >
> > > ### CLI
> > >
> > > ```bash
> > > # WHY query
> > > coherence iris query --type WHY --target ep-001
> > >
> > > # STATUS query (no target required)
> > > coherence iris query --type STATUS
> > >
> > > # WHAT_DRIFTED with JSON output
> > > coherence iris query --type WHAT_DRIFTED --json
> > >
> > > # RECALL with custom limit
> > > coherence iris query --type RECALL --target ep-042 --limit 10
> > > ```
> > >
> > > ### JSON Schema
> > >
> > > The query/response contract is formally defined in `specs/iris_query.schema.json` (JSON Schema draft 2020-12, `$id: https://deepsigma.dev/schemas/iris_query.schema.json`). Validate with any JSON Schema 2020-12 compliant validator.
> > >
> > > ### Dashboard
> > >
> > > The Σ OVERWATCH dashboard includes an IRIS Query Panel (view 4, keyboard shortcut `4`). The operator types a natural-language question, selects a query type, and receives a structured response with full provenance chain visualization. See `dashboard/src/IrisPanel.tsx`.
> > >
> > > ---
> > >
> > > ## 7) Usage Patterns
> > >
> > > ### Post-Incident Review
> > >
> > > After a decision produces an unexpected outcome, the operator runs a WHY query against the episode ID. IRIS returns the Memory Graph provenance (what evidence was used, what actions were taken), the DLR policy context (was a degrade step active? was the policy stamp present?), and any linked drift events. This replaces ad-hoc log grep with structured, provenanced answers.
> > >
> > > ### Drift Triage
> > >
> > > During routine monitoring, the operator runs a WHAT_DRIFTED query. IRIS returns the severity breakdown, top recurring fingerprints, and the MG resolution ratio. If the resolution ratio is low (many drifts, few patches), the operator knows the drift-to-patch loop is falling behind.
> > >
> > > ### Coherence Health Check
> > >
> > > Before a deployment or after a configuration change, the operator runs a STATUS query. IRIS returns the composite coherence score and per-dimension breakdown. If any dimension is below threshold (e.g., Drift Control < 60), the operator can drill into WHAT_DRIFTED for specifics.
> > >
> > > ### Institutional Memory Retrieval
> > >
> > > When a new team member asks "what do we know about decision class X?", the operator runs a RECALL query. IRIS returns the full graph context: provenance node, evidence refs, actions, drift history, applied patches, and DLR record. This is the sub-60-second institutional memory promise in action.
> > >
> > > ### Change Audit
> > >
> > > Before a policy pack update, the operator runs WHAT_CHANGED to understand the current state: how many episodes have been sealed, what the outcome distribution looks like, how many are missing policy stamps, and how many patches have been applied. This provides the baseline for measuring the impact of the policy change.
> > >
> > > ---
> > >
> > > ## 8) Configuration
> > >
> > > | Parameter | Default | Description |
> > > |-----------|---------|-------------|
> > > | `response_time_target_ms` | 60,000 | Wall-clock time (ms) before IRIS logs a performance warning |
> > > | `max_provenance_depth` | 50 | Maximum number of provenance links per response |
> > > | `default_time_window_seconds` | 3,600 | Default time window for time-bounded queries (WHAT_CHANGED) |
> > > | `default_limit` | 20 | Default result count limit |
> > > | `include_raw_artifacts` | false | If true, include raw artifact data in the response `data` field |
> > >
> > > Configuration validation runs at engine construction time. Invalid configurations (e.g., negative `response_time_target_ms`) raise `ValueError`.
> > >
> > > ---
> > >
> > > ## 9) Artifact Files
> > >
> > > | File | Description |
> > > |------|-------------|
> > > | `coherence_ops/iris.py` | IRIS engine implementation — query resolution, provenance assembly, confidence scoring |
> > > | `specs/iris_query.schema.json` | JSON Schema contract for IRIS query and response formats |
> > > | `coherence_ops/cli.py` | CLI integration — `coherence iris query` command |
> > > | `dashboard/src/IrisPanel.tsx` | Dashboard IRIS Query Panel component |
> > > | `dashboard/src/mockData.ts` | Mock IRIS resolver for dashboard dev mode |
> > >
> > > ---
> > >
> > > ## 10) Glossary Cross-Reference
> > >
> > > Key terms used in this document are defined in [GLOSSARY.md](../GLOSSARY.md):
> > >
> > > | Term | Glossary Definition |
> > > |------|-------------------|
> > > | **IRIS** | The operator-facing interface layer. Provides query resolution with sub-60-second response targets. |
> > > | **PRIME** | The governance threshold gate. Converts LLM probability gradients into decision-grade actions. |
> > > | **DLR** | Decision Lineage Record — the truth constitution for a decision class. |
> > > | **RS** | Reasoning Summary — aggregates sealed episodes into learning summaries. |
> > > | **DS** | Drift Scan — collects and structures runtime drift signals. |
> > > | **MG** | Memory Graph — provenance and recall graph enabling sub-60-second retrieval. |
> > > | **Claim–Evidence–Source** | The truth chain: every assertion must link to evidence, which must link to a source. |
> > > | **Coherence Score** | Unified 0–100 score computed from all four artifact layers. |
> > > | **Seal / Sealing** | Making a record immutable and tamper-evident. |
> > >
> > > See also: [01-language-map.md](01-language-map.md) for the full mapping of LinkedIn content concepts to repository artifacts, including IRIS at Phase 2.
> > >
> > > ---
> > >
> > > See also:
> > > - [00-vision.md](00-vision.md) — project vision
> > > - - [02-core-concepts.md](02-core-concepts.md) — DTE, Safe Action Contract, DecisionEpisode, DriftEvent
> > >   - - [10-coherence-ops-integration.md](10-coherence-ops-integration.md) — canonical artifact mapping (DLR/RS/DS/MG)
> > >     - - [17-prompt-to-coherence-ops.md](17-prompt-to-coherence-ops.md) — Prompt Engineering to Coherence Engineering
