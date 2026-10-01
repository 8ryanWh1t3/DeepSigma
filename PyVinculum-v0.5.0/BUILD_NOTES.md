# Build Notes — VINCULUM pyLib v0.5.0

Release name: **P↔D Tension Engine**

Core pipeline:

```text
INGEST → DECOMPOSE → SCORE P → SCORE D → DERIVE V/τ → AGGREGATE → EXPLAIN
```

The package is intentionally deterministic and inspectable. Default scoring is rule/structure based; no LLM is invoked by the core.

Runtime dependency: `rdflib>=7.0` for Turtle/RDF parsing.

See `VALIDATION.md` for build/test evidence and `MANIFEST.sha256` for file integrity.
