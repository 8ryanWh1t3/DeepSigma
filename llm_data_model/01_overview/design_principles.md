# Design Principles

Six principles govern the LLM Data Model.  Every schema decision, validation rule, and retrieval pattern traces back to one or more of these.

## 1. Provenance-first

Every record answers: *why do we believe this exists?*

- `source` — the system, actor, or sensor that produced the record.
- `provenance` — a structured chain: **Claim → Evidence → Source**.  A claim without evidence is just an assertion; evidence without a source is unverifiable.
- `confidence` — a 0–1 score plus a human-readable `explanation` so both agents and auditors can evaluate trust.

**Rule**: No record may be ingested without at least a `source` and a `confidence` value.  If the ingesting system cannot provide a confidence score, it must set `confidence.score: 0.0` and `confidence.explanation: "unscored"`.

## 2. TTL-native (Freshness)

Data expires.  Stale facts are worse than no facts because they create false confidence.

- `ttl` — time-to-live in milliseconds.  After this window, the record should be re-validated or excluded from reasoning.
- `assumption_half_life` — the half-life of the assumption embedded in the record.  After one half-life, confidence should be halved.  After two, it's nearly worthless.

**Rule**: Every record must have a `ttl`.  Records with `ttl: 0` are treated as "perpetual" (e.g., immutable policy documents).  The supervisor must check `ttl` against `observed_at` before allowing any agent to reason over the record.

**Alignment**: This mirrors the RAL freshness model — `context.ttlMs`, `context.maxFeatureAgeMs`, and the `freshness` block in DTEs.

## 3. Seal-on-write (Immutability)

Records are immutable once sealed.  You don't edit; you patch.

- `seal.hash` — SHA-256 of the record content at seal time.
- `seal.sealed_at` — ISO-8601 timestamp of when the seal was applied.
- `seal.version` — monotonically increasing version number.
- `seal.patch_log` — ordered list of patches applied, each with its own timestamp, author, reason, and new hash.

**Rule**: After sealing, only the `patch_log` field may be appended.  The original `content` is never mutated.  A patch creates a new version but preserves the full history.

**Alignment**: This mirrors DecisionEpisode sealing — once an episode's `seal.sealHash` is stamped, the episode is immutable evidence.

## 4. Graph-linked

Records form a knowledge graph.  Every record can link to any other record.

- `links` — an array of typed edges: `{ "rel": "supports", "target": "<record_id>" }`
- Standard edge types: `supports`, `contradicts`, `derived_from`, `supersedes`, `part_of`, `caused_by`, `verified_by`

**Rule**: Links are directional.  `A supports B` does not imply `B supports A`.  Bidirectional relationships should be recorded as two separate links.

**Alignment**: This maps directly to the Coherence Ops Memory Graph (MG), where nodes are canonical records and edges are typed relationships.

## 5. Schema-enforced

Every record validates against a JSON Schema before it enters the system.

- `02_schema/jsonschema/canonical_record.schema.json` defines the envelope.
- Type-specific payload schemas can extend `content` validation.
- The validation script (`05_validation/validate_examples.py`) runs against all examples on every CI build.

**Rule**: Invalid records are rejected at ingestion.  There are no "partial" records — either the envelope is complete and valid, or the record does not enter the system.

## 6. AI-retrievable

The data model is designed for three retrieval patterns working together:

- **Vector search** — semantic similarity over `content` and `provenance.explanation`
- **Keyword search** — exact match on `labels`, `record_type`, `source`
- **Graph traversal** — follow `links` edges to discover related records

**Rule**: Every record must have at least one `label` to enable keyword filtering.  The `content` field must be structured enough for embedding but readable enough for keyword extraction.

**Alignment**: The retrieval strategy is documented in `07_retrieval/indexing_strategy.md` and the top query patterns in `07_retrieval/query_patterns.md`.

## Principle interactions

These six principles reinforce each other:

- Provenance feeds **confidence** → confidence gates **retrieval** → retrieval respects **TTL** → TTL violations trigger **drift** → drift is recorded as a **sealed event** → events link via the **graph**.
- The graph enables auditors to walk the full evidence chain from any decision back to its original observations, with every hop carrying its own provenance, confidence, and freshness metadata.
