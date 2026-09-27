# pyOVIS v0.1.0 — Initial Release

**Release date:** 2026-09-27

## Mission

Provide a local, inspectable multimodal semantic discovery layer that can sit in front of Deep Sigma's governed reasoning stack.

## Included

- Text and common structured-text ingest
- PDF page-level text extraction
- Image/audio/video object ingest
- Optional Ovis-Omni-Embedding-3B backend
- Deterministic hash backend for tests and plumbing demos
- SQLite semantic object/vector store
- Cosine nearest-neighbor retrieval
- Semantic residual discovery
- SHA-256 provenance
- RESONATOR candidate-edge JSON export
- CLI
- Unit tests
- GitHub Actions CI/build workflows

## Explicitly excluded

- Authority determination
- RDF/SKOS mutation
- Ontology governance
- CERPA Apply
- Classification enforcement
- Model weights

## Acceptance evidence

- Python compile: PASS
- Unit tests: 4/4 PASS
- CLI init/ingest/stats/search: PASS
- RESONATOR export: PASS
- Export authority invariant: PASS (`authoritative=false`, `relationship=UNRESOLVED`)
- Wheel build: PASS

## Known limitation

The actual 3B Ovis model was not downloaded/executed in the packaging environment. The adapter is implemented against the current upstream Hugging Face/Transformers and Qwen Omni preprocessing interfaces; validate on the target GPU/runtime before operational use.
