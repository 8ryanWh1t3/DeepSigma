# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| main    | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Σ OVERWATCH / DeepSigma,
**please do not open a public issue.**

Instead, email **8ryanWh1t3@gmail.com** with:

1. A description of the vulnerability
2. Steps to reproduce
3. Impact assessment (if known)

You should receive an acknowledgement within **48 hours** and a detailed
response within **5 business days** indicating next steps.

## Scope

The following are in scope for security reports:

- **engine/** — supervisor scaffold, degrade ladder, policy loader
- **coherence_ops/** — audit, scoring, reconciler, memory graph
- **verifiers/** — read-after-write, invariant checks
- **tools/** — run_supervised, validate_examples, drift_to_patch
- **specs/** — JSON Schema definitions
- **policy_packs/** — versioned enforcement bundles

The following are out of scope:

- **mermaid/**, **wiki/**, **docs/** — documentation only (no executable code)
- **rdf/** — ontology and SPARQL definitions (no executable code)
- **dashboard/demo.html** — static demo file

## Disclosure Policy

- We will coordinate disclosure with the reporter.
- We aim to release a fix within **30 days** of confirmation.
- Credit will be given to reporters unless they prefer anonymity.

## Security Best Practices

This repo enforces:

- **SHACL validation** on all RDF ingestion (constitution layer)
- **Policy pack hash verification** before enforcement
- **Sealed DecisionEpisodes** — immutable after sealing
- **Named graph immutability** — patch-rather-than-overwrite
- **CODEOWNERS** review on all pull requests to protected paths
