# pyOVIS Architecture

## Purpose

pyOVIS converts heterogeneous artifacts into a shared semantic retrieval surface. It deliberately stops before semantic adjudication or authority.

```text
Artifact → Provenance → Embedding → Semantic Store → Retrieval Signal → Candidate Edge
```

## Components

- **ingest.py** — file discovery and modality-aware object creation
- **provenance.py** — SHA-256 and source metadata
- **embedder.py** — backend abstraction, deterministic test backend, Ovis backend
- **store.py** — SQLite object/vector persistence and brute-force cosine retrieval
- **search.py** — neighbor and residual logic
- **resonator.py** — downstream candidate-edge contract
- **cli.py** — operator surface

## Why SQLite

The initial release uses SQLite plus float32 vector blobs because it is portable, inspectable, disconnected-friendly, and easy to audit. The interface is intentionally simple so FAISS, sqlite-vec, pgvector, Qdrant, or another ANN layer can be added later without changing the candidate-edge contract.

## Authority boundary

The store contains observations and similarity results. It does not contain authoritative enterprise relationships. Candidate edges remain unresolved until downstream systems interpret and govern them.
