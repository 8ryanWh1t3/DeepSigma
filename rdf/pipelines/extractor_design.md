# SharePoint → RDF Extractor Design (v0.1)

## Objective
Convert document-centric KM into a meaning-centric graph that supports Coherence Ops.

## Pipeline (High Level)
1. **Ingest**
   - Read SharePoint items (doc + metadata + URL).
2. **Extract**
   - Identify candidates: Claims, Evidence, Sources, Decisions, Assumptions, Policies, Drift, Patch.
   - Prefer deterministic extraction where possible; use LLM only for classification/structuring.
3. **Normalize**
   - Canonical IDs (e.g., DEC_*, CL_*, EV_*, SRC_*).
   - De-duplicate by content hash and semantic similarity.
4. **Emit**
   - Turtle triples (`.ttl`)
   - Optional CSV audit logs
5. **Validate**
   - SHACL constraints (“constitution layer”)
6. **Serve**
   - SPARQL queries for executive retrieval
   - Subgraph packing for LLM context (graph-first grounding)

## Non-Goals (v0.1)
- Full authority precedence modeling (future)
- Full OWL reasoning (future)
- End-user UI (separate module)

## Outputs
- Minimal: `Source`, `Evidence`, `Claim`, `Decision`, `Assumption`
- Next: `DriftEvent`, `Patch`, `Episode`
