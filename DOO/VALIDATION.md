# DOO v0.2 Validation

- Turtle files: **10**
- Parse status: **PASS**
- Combined triples: **617**
- Classes: **41**
- Object properties: **47**
- Datatype properties: **21**
- Named individuals: **16**

## File parse results

| File | Parse | Triples |
|---|---:|---:|
| `doo-all.ttl` | PASS | 10 |
| `doo-authority.ttl` | PASS | 74 |
| `doo-coherenceops.ttl` | PASS | 33 |
| `doo-core.ttl` | PASS | 131 |
| `doo-evidence.ttl` | PASS | 91 |
| `doo-lifecycle.ttl` | PASS | 132 |
| `doo-memory.ttl` | PASS | 46 |
| `doo-provenance.ttl` | PASS | 26 |
| `doo-shapes.ttl` | PASS | 49 |
| `examples/decision-episode-example.ttl` | PASS | 25 |

Validation performed with `rdflib` Turtle parsing. This confirms RDF syntax and graph construction; it is not a complete OWL-DL consistency proof or SHACL conformance run.
