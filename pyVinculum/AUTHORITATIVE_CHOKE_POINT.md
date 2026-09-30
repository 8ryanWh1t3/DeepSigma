# VINCULUM v0.4 — Authoritative Choke Point

## The problem v0.4 closes

v0.3 could answer:

> Is this governance state authentic under the pinned root and monotonic trust history?

That is necessary but not sufficient for DOC COMPOSER integration.

A caller could still possess a valid signed bundle that was never actually published as the current enterprise state.

v0.4 therefore separates:

```text
VALID SIGNATURE
from
CURRENT AUTHORITATIVE PUBLICATION
```

## Reference choke point

```text
DOC COMPOSER
    │
    └─ ComposerChange
          ↓
      PREPARE
          ↓
      CommitIntent
          ↓
  ROOT SIGNER / HSM / KMS
          ↓
      SIGNATURE
          ↓
       COMMIT
          ↓
AUTHORITATIVE STATE STORE
          ↓
READ-ONLY VINCULUM RUNTIME
```

## PREPARE contract

The prepared intent fixes:

- producer = `COMPOSER`;
- change ID;
- artifact ID;
- revision;
- exact governance context SHA-256;
- next epoch;
- exact current bundle hash;
- exact current commit-record hash.

Those facts are incorporated into the root-signed bundle metadata.

## COMMIT contract

COMMIT succeeds only if:

```text
root signature valid
AND signed bytes exactly reconstruct prepared intent
AND deployment/root identities match
AND repository history verifies
AND epoch is exactly current + 1
AND supersedes_hash == current bundle hash
AND previous_commit_sha256 == current commit-record hash
AND commit record persists + reads back
AND HEAD persists + reads back
AND post-commit repository state reconstructs the expected receipt
```

## Bypass rule

A caller may still use lower-level VINCULUM analysis APIs for non-authoritative work.

But it cannot produce an `AuthoritativeBinding` by passing:

- its own `GovernanceContext`;
- its own `SignedGovernanceBundle`;
- its own `AuthoritativeCommitReceipt`.

`bind_authoritative()` re-reads the repository through `AuthoritativeGovernanceRuntime`.

## External DOC COMPOSER integration requirement

The library can enforce its own authoritative API boundary. It cannot prove that a separate DOC COMPOSER executable has no alternate database write route.

For full product integration, DOC COMPOSER must implement:

```text
ANY authoritative mutation
        ↓
ONE commit/publish service
        ↓
VINCULUM authoritative store contract
```

Any second mutation route is a product-level bypass and should be treated as a release blocker.

## Production signer rule

The reference services do not require the root private key.

Production should send:

```text
CommitIntent.signing_bytes()
```

to an external signer and receive only the signature.

The root private key should never be embedded in a VINCULUM application artifact.
