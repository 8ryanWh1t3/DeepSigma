# LLM Data Model

> Make your data AI-readable, auditable, and retrievable — with **Truth · Reasoning · Memory** baked in.

## One-command demo

```bash
python llm_data_model/05_validation/validate_examples.py
```

This validates every example in `03_examples/` against the canonical record schema, prints a sample retrieval query, and exits 0 on success.

## Folder structure

```
llm_data_model/
├── README.md                          ← you are here
├── 01_overview/
│   ├── llm_data_model_onepager.md     ← what this is, why it matters
│   └── design_principles.md           ← provenance, TTL, sealing, patching
├── 02_schema/
│   ├── canonical_record.json          ← the envelope every record uses
│   ├── field_dictionary.md            ← every field: meaning, type, examples
│   └── jsonschema/
│       └── canonical_record.schema.json
├── 03_examples/
│   ├── claim_record.json
│   ├── decision_episode.json
│   ├── document_record.json
│   ├── event_record.json
│   └── entity_record.json
├── 04_mappings/
│   ├── legacy_to_llm_mapping.csv
│   ├── sharepoint_mapping.md
│   ├── palantir_mapping.md
│   └── power_platform_mapping.md
├── 05_validation/
│   ├── validate_examples.py
│   └── quality_rules.md
├── 06_ontology/
│   ├── node_types.md
│   ├── edge_types.md
│   └── coherence_ops_alignment.md
├── 07_retrieval/
│   ├── indexing_strategy.md
│   └── query_patterns.md
├── 08_governance/
│   ├── access_control.md
│   ├── sealing_and_versioning.md
│   └── retention_and_redaction.md
├── 09_connectors/
│   ├── ingest_contracts.md
│   └── mcp_notes.md
└── 10_changelog/
    └── CHANGELOG.md
```

## The Canonical Record Envelope

Every object in the data model wraps itself in a standard envelope.  This is the AI-native "data constitution."

| Field | Purpose |
|---|---|
| `record_id` | Stable UUID — never reused |
| `record_type` | `Claim` \| `DecisionEpisode` \| `Event` \| `Document` \| `Entity` \| `Metric` |
| `created_at`, `observed_at` | ISO-8601 timestamps |
| `source` | System/actor that produced the record |
| `provenance` | Chain: Claim → Evidence → Source |
| `confidence` | 0–1 score + human-readable explanation |
| `ttl` / `assumption_half_life` | Freshness expiry rules (ms) |
| `labels` | Domain tags, sensitivity tier, project |
| `links` | Graph edges: `supports`, `contradicts`, `derived_from`, … |
| `content` | The actual payload (type-specific) |
| `seal` | Hash + signature + version + patch_log |

## Alignment with Σ OVERWATCH

The LLM Data Model is the **persistence layer** that feeds Σ OVERWATCH's runtime:

| RAL concept | Data model record type |
|---|---|
| DecisionEpisode | `DecisionEpisode` record (sealed, immutable) |
| Action Contract | Embedded in episode `content.actions[]` |
| Drift Event | `Event` record with `labels.domain = "drift"` |
| DTE | `Document` record capturing the envelope definition |
| Policy Pack | `Document` record with `labels.domain = "policy"` |
| Coherence Ops artifacts | `Claim` / `Entity` records linked via `coherence_ops_alignment` |

## Design principles (summary)

1. **Provenance-first** — every record says *why we believe it exists*.
2. **TTL-native** — data expires; stale facts are worse than no facts.
3. **Seal-on-write** — records are immutable once sealed; changes go through `patch_log`.
4. **Graph-linked** — records form a knowledge graph via typed `links`.
5. **Schema-enforced** — every record validates against `canonical_record.schema.json`.
6. **AI-retrievable** — designed for vector + keyword + graph retrieval patterns.

## Quick links

| Resource | Path |
|---|---|
| One-pager | [`01_overview/llm_data_model_onepager.md`](01_overview/llm_data_model_onepager.md) |
| Canonical schema | [`02_schema/jsonschema/canonical_record.schema.json`](02_schema/jsonschema/canonical_record.schema.json) |
| Examples | [`03_examples/`](03_examples/) |
| Validation script | [`05_validation/validate_examples.py`](05_validation/validate_examples.py) |
| Ontology | [`06_ontology/`](06_ontology/) |
| Retrieval patterns | [`07_retrieval/query_patterns.md`](07_retrieval/query_patterns.md) |
