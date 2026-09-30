# Changelog

## 0.4.0 — Authoritative Choke-Point Integration

### Added

- `ComposerChange` stable change identity.
- `CommitIntent` PREPARE object with exact epoch and predecessor binding.
- external-signing byte contract; commit services never require root private key.
- `FileAuthoritativeStateStore` append-only authoritative repository.
- HMAC-protected deployment marker, HEAD, and immutable commit records.
- double lineage: bundle `supersedes_hash` + commit-record predecessor hash.
- optimistic PREPARE / stale-COMMIT rejection.
- full reachable authoritative-history verification.
- read-only `AuthoritativeGovernanceRuntime`.
- `VinculumEngine.bind_authoritative()`.
- `AuthoritativeBinding` combining result + trust + publication receipt.
- `CerpaHandoff` and `CerpaBridge` REVIEW / APPLY freshness guard.
- `GovernancePolicy.authoritative()` label with unchanged v0.3 governance semantics.
- authoritative reference example and integration documentation.

### Preserved

- v0.1 P + D → B behavior.
- v0.2 evidence/provenance/authority governance.
- v0.3 signed-bundle and durable anti-rollback APIs.
- v0.3 trusted-governance bundle schema.

### Explicitly not claimed

- that an external DOC COMPOSER binary has no alternate mutation route;
- that VINCULUM itself performs CERPA APPLY;
- that file-backed reference storage replaces enterprise repository/HSM controls.
