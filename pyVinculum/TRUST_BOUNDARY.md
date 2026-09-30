# VINCULUM v0.4 — Trust and Authority Boundary

## What v0.4 proves in the reference implementation

Given a correctly provisioned root and protected authoritative-store integrity key, VINCULUM can prove that:

- the governance bundle is signed by the pinned Ed25519 root;
- the bundle belongs to the expected deployment;
- the governance context matches its declared SHA-256;
- COMPOSER publication epochs do not move backward or skip;
- each bundle supersedes the exact previous bundle;
- each commit record references the exact previous commit record;
- the current state exists in an append-only authoritative repository;
- the reachable publication history is complete and internally coherent;
- a signed but uncommitted bundle cannot drive `bind_authoritative()`;
- a stale prepared commit cannot overwrite a newer COMPOSER HEAD;
- corruption/loss of initialized authoritative state fails closed;
- an authoritative binding records the exact trust and publication receipts used;
- CERPA handoff fails if authoritative state changes before its apply guard.

## What v0.4 does not claim

The library cannot independently prove that:

- an external DOC COMPOSER application has no bypassing write API;
- the pinned root public key was provisioned by the correct enterprise authority;
- the root private key / HSM / KMS has not been compromised;
- the host OS is uncompromised;
- the repository integrity key is securely stored;
- a fully privileged administrator cannot destroy and deliberately reprovision the entire deployment;
- CERPA itself correctly enforces every downstream human/enterprise authorization.

Those are deployment/product/system properties.

## Production posture

```text
OFFLINE/HSM/KMS ROOT PRIVATE KEY
             │
             │ signs exact CommitIntent bytes
             ▼
DOC COMPOSER AUTHORITATIVE COMMIT SERVICE
             │
             ▼
TRANSACTIONAL / APPEND-ONLY AUTHORITATIVE REPOSITORY
             │
             ▼
READ-ONLY VINCULUM AUTHORITATIVE RUNTIME
             │
             ▼
BOUNDED COHERENCE
             │
             ▼
CERPA REVIEW + APPLY AUTHORITY
```

## Root rule

> **Application code may read the root. It may not establish or replace the root.**

## Publication rule

> **A valid signature authenticates a state. Only the authoritative commit path publishes that state.**

## History rule

> **Loss of authoritative history is not permission to create a new history.**

## Action rule

> **A VINCULUM bound result is evidence for CERPA review. It is not self-originating authority to APPLY.**
