# Security and trust boundaries — v0.7.0

This library is reference software for representations and review findings. It is not safety-certified, an authority system, a classified-data boundary, or a substitute for secure deployment engineering.

## Input boundary

- Jobs are strict declarative JSON/YAML data, not executable code.
- Local path loading is explicit and confined to the supplied base directory after path resolution. Symlink escapes are rejected. This is not a defense against a hostile local administrator or filesystem race.
- Expected hashes detect differing bytes; they do not authenticate sources. Sources with no byte hash are openly marked reference-only.
- YAML aliases, duplicate keys and unsafe tags are rejected.
- Local RDF parsing does not fetch user-specified web resources or infer numeric semantics.
- Bounds restrict file size, row/page counts, expanded data and graph/pair budgets. They are not an operating-system resource sandbox. Document parsers can allocate memory while decoding; isolate untrusted parsers in constrained processes.
- User-authored local regex lexicons are trusted configuration. HTTP jobs cannot submit them. A Python regular expression engine is not guaranteed free of catastrophic backtracking for hostile patterns.
- `interval_calculate` uses a restricted AST, not eval or exec. Only finite scalar intervals, names, numeric constants, unary signs and + - * / are allowed. Units must be modeled by the caller.

## Pairing and support

Matching is metadata-based, not numeric similarity. Missing information, known mismatch and weak support have separate states. Auto pairing requires an explicit named policy. Evidence ancestry and common roots are surfaced. Multiple displays of the same evidence are not independent experiments.

Missing source registration can be a required unresolved check. With optional registration, missing ancestry withholds supported scores but does not fabricate a raw conflict or agreement. No score certifies an entity, threat, person or action.

## Outputs

HTML escapes source text and carries a restrictive CSP, with no JavaScript or remote assets. CSV/XLSX formula-like strings are escaped. Markdown summary text is escaped rather than emitted as active raw HTML. Do not execute content extracted from a document.

All reports may contain the submitted source text and identifiers. Access, retention, redaction, classification and release policy remain the deploying application's responsibilities.

The SQLite archive uses parameterized operations and content hashes. It detects changed stored payloads on read but cannot prevent an attacker with write access from replacing both data and hash. It is not an append-only trusted ledger or enterprise root of trust.

## HTTP facade

No listener starts on import. The optional FastAPI application requires a bearer token unless an unauthenticated demo is explicitly enabled. HTTP requests are bounded; paths, remote URLs, client regex configuration and arbitrary plugins are prohibited. Use TLS, a managed identity gateway, rate limits, request/process deadlines and resource isolation in a real deployment. The reference token check is not production IAM.

The release tests use TestClient, not a security audit of a deployed service. No live Lattice/Foundry/Vantage/OnBase connection has been exercised.
