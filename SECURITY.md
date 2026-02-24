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

- **src/core/** — CORE audit, scoring, reconciler, memory graph
- **enterprise/src/** — ENTERPRISE adapters, services, governance modules
- **enterprise/schemas/** — JSON Schema definitions
- **enterprise/policy_packs/** — versioned enforcement bundles

The following are out of scope:

- **enterprise/docs/mermaid/**, **enterprise/docs/wiki/**, **docs/** — documentation only
- **enterprise/docs/rdf/** — ontology and SPARQL definitions (no executable code)
- **enterprise/dashboard/demo.html** — static demo file

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

## Release Signature Verification

Tagged releases (`v*`) publish signed artifacts and SBOM evidence:

- Python distributions (`.whl`, `.tar.gz`) are signed with **Sigstore keyless** and include `*.sigstore.json` bundles.
- Container image `ghcr.io/8ryanwh1t3/deepsigma` is signed with **Cosign keyless**.
- SBOMs are attached to release artifacts:
  - `deepsigma-<tag>-source.sbom.cdx.json` (CycloneDX)
  - `deepsigma-<tag>-image.sbom.spdx.json` (SPDX)

### Verify Python release signatures

```bash
python -m pip install sigstore
python -m sigstore verify github \
  --bundle deepsigma-<version>-py3-none-any.whl.sigstore.json \
  --repository 8ryanWh1t3/DeepSigma \
  --trigger push \
  --name CI \
  --ref refs/tags/v<version> \
  deepsigma-<version>-py3-none-any.whl
```

### Verify container signature

```bash
cosign verify \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp '^https://github.com/8ryanWh1t3/DeepSigma/.github/workflows/ci.yml@refs/tags/v<version>$' \
  ghcr.io/8ryanwh1t3/deepsigma:v<version>
```
