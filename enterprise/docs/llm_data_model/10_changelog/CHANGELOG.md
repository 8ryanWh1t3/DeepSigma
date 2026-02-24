# Changelog

All notable changes to the LLM Data Model specification.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-02-12

### Added

- **Canonical Record Envelope** — the standard wrapper for every data object (`02_schema/`)
- **JSON Schema** — `canonical_record.schema.json` for structural validation
- **Field Dictionary** — complete field reference with types, constraints, and examples
- **5 example records** — Claim, DecisionEpisode, Document, Event, Entity (`03_examples/`)
- **Legacy mappings** — CSV mapping file + SharePoint, Palantir, Power Platform mapping docs (`04_mappings/`)
- **Validation script** — `validate_examples.py` one-command demo (`05_validation/`)
- **Quality rules** — 20+ semantic validation rules with REJECT/WARN severity (`05_validation/`)
- **Ontology** — node types, edge types, and Coherence Ops alignment (`06_ontology/`)
- **Retrieval strategy** — vector + keyword + graph indexing strategy (`07_retrieval/`)
- **Query patterns** — top 20 queries the model must support (`07_retrieval/`)
- **Governance** — access control, sealing/versioning, retention/redaction (`08_governance/`)
- **Connectors** — ingest contracts and MCP integration notes (`09_connectors/`)
- **Design principles** — provenance-first, TTL-native, seal-on-write, graph-linked, schema-enforced, AI-retrievable

### Schema version

- `canonical_record.schema.json` — v1.0.0
- 6 record types: Claim, DecisionEpisode, Event, Document, Entity, Metric
- 7 edge types: supports, contradicts, derived_from, supersedes, part_of, caused_by, verified_by
- 5 sensitivity tiers: public, internal, confidential, restricted, high
