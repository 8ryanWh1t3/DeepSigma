# Changelog

All notable changes to Σ OVERWATCH / DeepSigma will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-02-13

### Added

- **Engine**: supervisor scaffold, degrade ladder, policy loader
- **Coherence Ops**: DLR builder, reflection session, drift signal collector, memory graph, auditor, scorer, reconciler, CLI (`coherence audit|score|mg|demo`)
- **Verifiers**: read-after-write, invariant check stubs
- **Specs**: JSON Schemas for Episode, DTE, Action Contract, Drift, Policy Pack
- **Policy Packs**: versioned enforcement bundles with hash verification
- **Tools**: `run_supervised.py`, `validate_examples.py`, `drift_to_patch.py`, `replay_episode.py`
- **Adapters**: MCP JSON-RPC scaffold, OpenClaw skill runner scaffold, OTel exporter placeholder
- **Dashboard**: interactive monitoring demo (HTML + React build)
- **LLM Data Model**: canonical record envelope, 6 record types, schemas, mappings, validation, retrieval, ontology
- **RDF Semantic Layer**: OWL ontology (Core 8 classes), SHACL shapes, SPARQL executive queries, SharePoint→RDF mappings
- **Mermaid Diagrams**: 26 diagrams covering architecture, runtime, schemas, coherence ops, LLM data model, and RDF layer
- **Examples**: demo-stack (4 scenarios), episodes, drift events, DTE packs, MCP samples
- **Docs**: 16 documentation files covering all modules
- **Wiki**: 48 pages covering concepts, schemas, integrations, governance, and visual documentation

### Infrastructure

- **CI**: GitHub Actions with pytest (3.10/3.11/3.12), ruff lint, and schema validation
- **Packaging**: `pyproject.toml` with console scripts (`overwatch`, `overwatch-validate`, `coherence`)
- **Repo Governance**: SECURITY.md, CODEOWNERS, Dependabot, issue/PR templates, CONTRIBUTING.md

### One-Command Demo

```bash
pip install -e .
overwatch \
  --decisionType AccountQuarantine \
  --policy policy_packs/packs/demo_policy_pack_v1.json \
  --telemetry endToEndMs=95 p99Ms=160 jitterMs=70 \
  --context ttlBreachesCount=0 maxFeatureAgeMs=180 \
  --verification pass \
  --out episodes_out
```

```bash
coherence demo
```

[0.1.0]: https://github.com/8ryanWh1t3/DeepSigma/releases/tag/v0.1.0
