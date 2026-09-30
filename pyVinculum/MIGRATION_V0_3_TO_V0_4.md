# Migration — VINCULUM v0.3 → v0.4

## No forced migration

Existing v0.3 code continues to work:

```python
engine.bind_trusted(..., runtime=TrustedGovernanceRuntime(...))
```

v0.4 does not silently reinterpret that call as COMPOSER-authoritative.

## To adopt authoritative mode

Replace the caller-supplied trusted-bundle workflow with:

```text
AuthoritativeBootstrapService      # deployment only
AuthoritativeCommitService         # all later COMPOSER publications
FileAuthoritativeStateStore        # reference repository
AuthoritativeGovernanceRuntime     # read-only decision runtime
VinculumEngine.bind_authoritative  # authoritative binding
CerpaBridge                         # downstream review/apply freshness
```

## Key operational change

v0.3:

```text
valid signed bundle
→ trusted runtime
→ trusted binding
```

v0.4 authoritative mode:

```text
COMPOSER PREPARE
→ external signature
→ committed authoritative repository state
→ read-only runtime
→ authoritative binding
→ CERPA freshness guard
```

## Root private key

Do not migrate root private-key custody into VINCULUM. `CommitIntent.signing_bytes()` exists specifically so production can keep signing in an HSM/KMS/offline authority service.
