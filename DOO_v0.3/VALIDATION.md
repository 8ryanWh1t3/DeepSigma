# DOO v0.3 Validation

- Turtle files: **18**
- Parse status: **PASS**
- Combined unique triples: **1205**
- Classes: **51**
- Object properties: **75**
- Datatype properties: **45**
- Named individuals: **21**
- Namespace isolation check: **PASS**
- Required-term check: **PASS**
- CORE example acceptance: **PASS**
- GOVERNED example acceptance: **PASS**

## File parse results

| File | Parse | Triples |
|---|---:|---:|
| `doo-all.ttl` | PASS | 12 |
| `doo-anatomy.ttl` | PASS | 120 |
| `doo-authority.ttl` | PASS | 102 |
| `doo-coherenceops.ttl` | PASS | 36 |
| `doo-core.ttl` | PASS | 161 |
| `doo-evidence.ttl` | PASS | 108 |
| `doo-lifecycle.ttl` | PASS | 217 |
| `doo-memory.ttl` | PASS | 63 |
| `doo-profiles.ttl` | PASS | 49 |
| `doo-provenance.ttl` | PASS | 36 |
| `doo-shapes-core.ttl` | PASS | 58 |
| `doo-shapes-evidence.ttl` | PASS | 42 |
| `doo-shapes-governed.ttl` | PASS | 41 |
| `doo-shapes-replay.ttl` | PASS | 29 |
| `doo-shapes.ttl` | PASS | 7 |
| `examples/governed-decision.ttl` | PASS | 94 |
| `examples/minimal-decision.ttl` | PASS | 27 |
| `migration/v0.1-to-v0.3.ttl` | PASS | 18 |

Validation uses `rdflib` Turtle parsing plus the shipped profile acceptance harness. The SHACL graphs are syntax-validated but a full standards-complete SHACL engine was not available in this build environment; therefore this report does not claim full SHACL conformance execution or a complete OWL-DL consistency proof.

## Query execution

All five shipped SPARQL examples parsed and executed successfully against the bundled governed-decision graph plus ontology modules. Queries that had no matching fixture data correctly returned zero rows rather than errors.
