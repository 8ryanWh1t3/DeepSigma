# VINCULUM pyLib v0.4.0 — Architecture

## 1. Purpose

VINCULUM models a distinction that ordinary AI workflows frequently collapse:

```text
probability ≠ permission
confidence  ≠ authority
signature   ≠ authoritative publication
```

The kernel keeps those concerns separate and then binds them deliberately.

```text
P candidate
   │
   ├───────────── evidence / provenance
   ▼
D constraints ─── authority / provenance
   │
   ▼
G governance context
   │
   ▼
T root-authenticated state
   │
   ▼
A COMPOSER committed authoritative state
   │
   ▼
VINCULUM
   │
   ▼
B bounded coherence
   │
   ▼
CERPA review / guarded apply handoff
```

v0.4's architectural contribution is **A**: cryptographically valid governance becomes authoritative only after it is committed through the controlled COMPOSER publication path.

## 2. Existing layers retained

### P — Hypothesis

`Hypothesis` preserves a declared probability and its evidence/provenance references. VINCULUM does not manufacture the probability.

### D — Constraint

`Constraint` deterministically produces `PASS`, `FAIL`, or `UNKNOWN`. Hard rules govern admissibility. Soft rules influence fit only.

### G — Governance

`GovernanceContext` materializes evidence, provenance, and authority. Its canonical SHA-256 binds a result to the governance facts actually evaluated.

### T — Trust

v0.3 `SignedGovernanceBundle`, `RootTrustAnchor`, and durable anti-rollback machinery remain supported. Root authentication proves who signed a state and its monotonic relation to trusted history.

## 3. New layer A — Authoritative publication

The v0.4 reference publication flow is:

```text
ComposerChange
     ↓
AuthoritativeCommitService.prepare()
     ↓
CommitIntent
     │
     ├─ next epoch
     ├─ current bundle hash
     ├─ current commit-record hash
     ├─ exact GovernanceContext
     └─ exact COMPOSER change identity
     ↓
external signer / HSM / KMS
     ↓
signature
     ↓
AuthoritativeCommitService.commit()
     ↓
FileAuthoritativeStateStore
```

The commit service itself has no root private-key setter or signing method.

## 4. Why two predecessor hashes exist

A v0.4 transition binds two chains:

```text
Governance-state chain:
Bundle N+1.supersedes_hash = SHA256(Bundle N)

Publication-record chain:
Commit N+1.previous_commit_sha256 = SHA256(CommitRecord N)
```

The first protects semantic/governance state lineage.
The second protects the publication event/history around that state.

Both must advance together.

## 5. Authoritative file-store transaction

For a new commit:

```text
1. Read + validate current HEAD.
2. Verify complete reachable history.
3. Require prepared epoch == HEAD epoch + 1.
4. Require exact predecessor bundle hash.
5. Require exact predecessor commit-record hash.
6. Verify root signature over exact prepared intent-derived bundle.
7. Write immutable commit record.
8. fsync commit record.
9. Read it back and compare.
10. Atomically replace HEAD.
11. fsync HEAD/directory.
12. Read HEAD back and compare.
13. Re-load the authoritative state and compare the receipt.
```

The record is written before HEAD. Therefore an interrupted commit can leave an orphan record, but old HEAD remains authoritative.

## 6. PREPARE is optimistic, COMMIT is authoritative

`prepare()` does not lock the repository. This is intentional.

Two writers may both prepare epoch N+1. Only one can commit against the current HEAD. The other is rejected as `STALE_COMMIT_INTENT`.

This prevents a stale pre-signed state from becoming authoritative after another valid publication has already moved the enterprise state.

## 7. Read/write separation

### Write plane

Only:

```text
AuthoritativeBootstrapService
AuthoritativeCommitService
```

can drive the reference authoritative store API.

### Read plane

`AuthoritativeGovernanceRuntime` exposes current committed state and performs full-chain verification by default.

It deliberately has no:

```text
commit
advance
bootstrap
set_root
```

## 8. Binding plane

`VinculumEngine.bind_authoritative()` accepts only `AuthoritativeGovernanceRuntime`.

It does not accept:

```text
GovernanceContext
SignedGovernanceBundle
AuthoritativeCommitReceipt
```

from the caller.

The runtime re-reads the repository and supplies the context and receipts.

The result is:

```text
AuthoritativeBinding
├─ BindingReport
├─ TrustReceipt
└─ AuthoritativeCommitReceipt
```

## 9. CERPA boundary

VINCULUM's output is not an APPLY operation.

`CerpaBridge` creates a REVIEW handoff that binds:

- binding hash;
- binding-report hash;
- authoritative-commit hash;
- commit-record hash;
- bundle hash;
- governance-context hash;
- result states.

Immediately before CERPA APPLY, `validate_apply_guard()` re-reads COMPOSER authoritative state.

```text
state unchanged → APPLY_GUARD
state changed   → STALE_AUTHORITATIVE_STATE
```

CERPA still owns its own review, patch, authority, and apply semantics.

## 10. Compatibility

The existing layers are not removed:

```text
bind()               analysis / compatibility
bind_trusted()       root-signed trusted-state path
bind_authoritative() COMPOSER committed-state path
```

The distinction is intentional. v0.4 does not call old analysis output authoritative merely because a newer library version exists.

## 11. Production substitution points

The file store is a reference adapter. A production implementation can replace it with:

- transactional relational repository;
- append-only event store;
- signed object store + transactional HEAD;
- HSM/KMS-backed state service;
- protected enterprise configuration repository.

The invariant to preserve is not the filesystem layout. It is:

> **There is one authoritative publication state, every transition is predecessor-bound, and VINCULUM reads it rather than accepting authoritative state from the candidate side.**
