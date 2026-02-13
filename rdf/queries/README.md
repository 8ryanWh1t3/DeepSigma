# SPARQL Queries (Proof of Value)

These queries are designed to demonstrate decision lineage + drift governance:
- Expired assumptions in active decisions
- Evidence/claim contradictions
- "Why retrieval" (Claim → Evidence → SourceArtifact)
- Drift → Patch traceability
- Source-of-truth rollup (latest sealed graph per entity)

Notes:
- Adjust graph patterns depending on your triplestore's named-graph conventions.
- If you store sealed episodes in named graphs, prefer `GRAPH ?g { ... }` patterns.
