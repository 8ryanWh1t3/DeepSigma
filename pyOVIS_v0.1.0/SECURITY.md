# Security Policy

## Scope

pyOVIS is a discovery and retrieval layer. It is **not** an access-control, classification, policy-authority, or adjudication system.

## Security invariants

- Never treat similarity as authority.
- Never expose source content without the caller's existing authorization.
- Preserve provenance for every object.
- Do not store credentials in metadata.
- Do not commit mission data or model caches to Git.
- Treat exported candidate edges as untrusted inputs to downstream governance.

## Reporting

Report security issues privately to the repository owner before opening a public issue.
