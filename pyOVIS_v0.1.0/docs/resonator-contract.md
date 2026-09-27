# RESONATOR Candidate-Edge Contract

Every exported edge MUST preserve the following invariant:

```json
{
  "relationship": "UNRESOLVED",
  "authoritative": false,
  "requires_resonator": true
}
```

Required fields:

- `type` = `SemanticCandidateEdge`
- `source`
- `candidate`
- `similarity`
- `relationship`
- `authoritative`
- `requires_resonator`
- `discovered_by`
- `discovery_method`
- `source_provenance`
- `candidate_provenance`

RESONATOR may classify the semantic relationship, detect contradictions, gaps, refinements, restrictions, implementation relationships, or other governed meanings. pyOVIS must not preempt that decision.
