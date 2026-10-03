# Security and application boundary

This build has automated regression/negative tests, not a third-party security review or safety certification.

## Core behavior

- No `eval`, pickle, downloaded models, executable scenario expressions, external signatures or command actions in the new pipeline.
- Scalar inputs reject booleans-as-counts, NaN and infinity. Numeric literal/size bounds and reference loader limits apply.
- JSON rejects duplicate keys and unknown typed fields.
- Exact rational conversions are used for registered units. Unknown units do not pass by string resemblance.
- Missing time/scope/concept does not turn into zero collision. Mandatory checks cannot be disabled by selecting fewer hinge orders.
- Dependency cycles are rejected and missing/shared dependence is reported.
- Report strings are HTML-escaped. Offline HTML uses a restrictive content-security policy and no JavaScript or network resources.
- CSV strings beginning with formula-like prefixes are escaped before spreadsheet consumption.
- A SHA-256 fingerprint establishes content identity, not authenticity, authority or protection against a host that can rewrite the files and hashes.

## RDF

The new RDF adapter accepts in-memory Turtle only. It does not accept a remote URL or expose JSON-LD context loading or SPARQL SERVICE. Native payload/projection disagreement is rejected. RDFLib is a general-purpose library with broader capabilities, so untrusted-data deployments should still isolate file and network access at the operating-system level. See official sources in SOURCES.md.

## Trusted extensions

Regex rules, unit registries, extraction plugins and custom hinge callbacks are trusted application configuration/code. An unrestricted plugin can execute arbitrary Python; the protocol is not a sandbox. Expensive regexes, very large graphs and deeply nested group hierarchies require application resource limits. The reference group hierarchy uses recursion; extremely deep hierarchies should be flattened by an adapter.

## Untested deployment surfaces

No live Lattice/Anduril, installation, aircraft, medical, payment, production database, distributed event bus, role-approval system or external LLM was connected. The monitor is local/in-memory and not a durable distributed stream processor. Training/illustrative reliability coefficients are not operational calibration evidence.
