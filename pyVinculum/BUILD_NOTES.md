# VINCULUM pyLib v0.4.0 — Build Notes

## Release theme

**Authoritative Choke-Point Integration**

v0.4 is deliberately a control-plane release rather than a new inference/scoring release.

The important transition is:

```text
v0.3
signed + trusted governance

v0.4
authenticated + COMPOSER-committed current governance
```

## New package modules

```text
vinculum.authoritative
vinculum.integration
```

## Primary new public APIs

```text
ComposerChange
CommitIntent
FileAuthoritativeStateStore
AuthoritativeBootstrapService
AuthoritativeCommitService
AuthoritativeGovernanceRuntime
AuthoritativeCommitReceipt
AuthoritativeBinding
CerpaHandoff
CerpaBridge
VinculumEngine.bind_authoritative()
GovernancePolicy.authoritative()
```

## Security/control posture

- Root private key is not required by the commit services.
- The root signer signs exact `CommitIntent.signing_bytes()` externally.
- COMPOSER publication uses optimistic PREPARE / exact COMMIT.
- Stale prepared intents fail if HEAD moved.
- Signed-but-uncommitted governance cannot drive authoritative binding.
- Current authoritative state is read from the repository at binding time.
- Full reachable publication history is verified by default.
- CERPA handoff is revalidated against current COMPOSER state before its apply guard.

## Compatibility posture

Core v0.3 semantic functions were not retuned. See `SEMANTIC_DELTA.md`.

## Test posture

```text
Source suite:           69 / 69 PASS
Installed-wheel suite:  69 / 69 PASS
Installed example:      BOUNDED_ACCEPTED + APPLY_GUARD
```

## Packaging note

The execution environment had no outbound package-index access, so the wheel was built using the locally installed build toolchain with build isolation disabled. Runtime dependency metadata still declares `cryptography>=43`.

## Next integration gate

The pyLib now contains the reference choke-point contract. The next proof should occur in the **actual DOC COMPOSER authoritative mutation path**:

```text
ANY authoritative DOC COMPOSER mutation
        ↓
ONE publish/commit service
        ↓
no alternate repository write path
```

That is a product-integration test, not another VINCULUM semantic feature.
