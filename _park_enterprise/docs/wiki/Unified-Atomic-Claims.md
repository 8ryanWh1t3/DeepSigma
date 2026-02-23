# Unified Atomic Claims

> Everything in Σ OVERWATCH is made of Claims.
>
> ## The Claim Primitive
>
> A **Claim** is the indivisible unit of asserted truth. It is the atom from which every governance structure is composed. Before Claims existed as a first-class primitive, truth lived in scattered places — inside episode context blobs, provenance chains, evidence ref arrays, and freeform content objects. Claims unify all of this into a single, validated, decaying, graph-linked, sealable object.
>
> **Schema**: [`specs/claim.schema.json`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/_park_enterprise/schemas/core/claim.schema.json)
> **Docs**: [`docs/19-claim-primitive.md`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/_park_enterprise/docs/19-claim-primitive.md)
>
> ## Anatomy of a Claim
>
> Every Claim has:
>
> | Field | What it does |
> |---|---|
> | `claimId` | Stable ID (`CLAIM-YYYY-NNNN`). Never reused. |
> | `statement` | One sentence, testable. The atomic truth. |
> | `scope` | Where + when + context. Bounded applicability. |
> | `truthType` | Epistemic class: observation, inference, assumption, forecast, norm, constraint |
> | `confidence` | 0.00–1.00 score + human explanation |
> | `statusLight` | 🟢🟡🔴 derived from confidence + source quality |
> | `sources[]` | Where the truth came from (typed, with reliability) |
> | `evidence[]` | What artifacts support it (typed, with method) |
> | `owner` | Accountable role (not a person) |
> | `halfLife` | How long before confidence halves. Includes `expiresAt` + `refreshTrigger`. |
> | `graph` | Typed edges: `dependsOn`, `contradicts`, `supersedes`, `patches`, `supports` |
> | `seal` | Immutable hash + version + append-only `patchLog` |
>
> ## Truth Types
>
> | Type | Meaning | Decays? |
> |---|---|---|
> | `observation` | Directly measured | Yes — sensors drift |
> | `inference` | Derived from evidence | Yes — premises change |
> | `assumption` | Taken as given | Yes — context shifts |
> | `forecast` | Predictive | Yes — future arrives |
> | `norm` | Policy or standard | Slow — policy updates |
> | `constraint` | Hard boundary | Rarely — regulatory change |
>
> ## Status Light Rules
>
> | Light | Rule |
> |---|---|
> | 🟢 **green** | confidence ≥ 0.80 AND ≥ 1 high-reliability source |
> | 🟡 **yellow** | confidence 0.50–0.79 OR mixed-reliability sources |
> | 🔴 **red** | confidence < 0.50 OR unresolved contradiction in `graph.contradicts` |
>
> ## Half-Life and Decay
>
> Claims are not eternal. Every Claim has a `halfLife` specifying how long its confidence remains valid. After one half-life, confidence should be halved. The `expiresAt` timestamp is computed from `timestampCreated + halfLife`. The `refreshTrigger` says what forces re-evaluation: expiry, contradiction, new source, or schedule.
>
> A Claim with `halfLife.value: 0` is **perpetual** (constraints, immutable policies).
>
> ## Claim Graph
>
> Claims form a directed graph:
>
> | Edge | Meaning |
> |---|---|
> | `dependsOn` | Requires these claims to be true |
> | `contradicts` | In active conflict — triggers 🔴 |
> | `supersedes` | Replaces a prior claim (never overwrite) |
> | `patches` | Patch IDs that modified meaning/confidence |
> | `supports` | Provides evidence for other claims |
>
> ## Claim-Native DLR
>
> The **Decision Log Record** has been refactored to be claim-native. Every DLR is now:
>
> 1. A categorised list of `claimRef`s across five stages: **context → rationale → action → verification → outcome**
> 2. 2. A `rationaleGraph` — directed edges between claims with types and confidence weights
>    3. 3. A `freshnessSnapshot` — was every claim fresh at decision time?
>      
>       4. Each `claimRef` carries a **decision-time snapshot**: the claim's confidence, statusLight, truthType, and freshness *at the moment the decision was made*. This means audit works even after claims expire or get superseded.
>      
>       5. **Schema**: [`specs/dlr.schema.json`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/_park_enterprise/schemas/core/dlr.schema.json)
>       6. **Docs**: [`docs/20-dlr-claim-native.md`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/_park_enterprise/docs/20-dlr-claim-native.md)
>      
>       7. ## Composability
>
> Once Claims exist as primitives, everything becomes a graph operation:
>
> | Operation | In Claim Terms |
> |---|---|
> | **DLR** | Subgraph query: which claims + edges governed this decision? |
> | **Canon** | Bless operation: promote claimIds to long-term memory |
> | **Drift** | Edge-weight change: confidence decayed, contradiction emerged, half-life expired |
> | **Retcon** | Supersede: create new claim version, link via `supersedes`, preserve original |
> | **Patch** | Append to `seal.patchLog`: modify without breaking immutability |
> | **IRIS** | Graph walk: follow `rationaleGraph` edges to answer WHY / WHAT_CHANGED / WHAT_DRIFTED |
> | **Reflection** | Aggregation: claim confidence distributions across episodes |
>
> ## Diagrams
>
> See [`archive/mermaid/27-claim-primitive.md`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/_park_enterprise/docs/archive/mermaid/27-claim-primitive.md) and [`archive/mermaid/28-dlr-claim-native.md`](https://github.com/8ryanWh1t3/DeepSigma/blob/main/_park_enterprise/docs/archive/mermaid/28-dlr-claim-native.md) for visual architecture.
>
> ## Related Pages
>
> - [Schemas](Schemas) — all JSON Schema specs
> - - [Contracts](Contracts) — DTE, Action Contract, Episode
>   - - [Coherence Ops Mapping](Coherence-Ops-Mapping) — DLR/RS/DS/MG
>     - - [Drift → Patch](Drift-to-Patch) — drift lifecycle
>       - - [Sealing & Episodes](Sealing-and-Episodes) — immutability model
>         - - [IRIS](IRIS) — query resolution engine
>           - - [LLM Data Model](LLM-Data-Model) — canonical record envelope
