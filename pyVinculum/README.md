# VINCULUM pyLib v0.4.0

**Probabilistic possibility + deterministic constraint + governed evidence + trusted authoritative state → bounded coherence.**

VINCULUM is a deterministic Python kernel that carries probabilistic candidates forward only after explicit constraints and governance facts have been evaluated.

v0.4 adds the **authoritative choke point** between COMPOSER and CERPA. The change is not a new semantic theory. It changes **where authoritative governance is allowed to come from and how a bound result is handed forward**.

```text
P = probabilistic candidate space
D = deterministic constraint space
G = evidence + provenance + authority
T = root-authenticated governance state
A = committed COMPOSER authoritative state

P + D + G, under T and A
              ↓
          VINCULUM
              ↓
       BOUNDED COHERENCE
              ↓
          CERPA REVIEW
```

The compact expression remains:

```text
P + D → B
B(x) = P(x) | D
```

v0.4 adds the operating rule:

> **A signed state is not authoritative merely because it is cryptographically valid. It must also be the current state committed through the COMPOSER authoritative repository.**

---

## What v0.4 adds

### 1. COMPOSER change identity

`ComposerChange` gives every authoritative publication a stable:

- change ID;
- artifact ID;
- revision;
- actor ID;
- reason;
- metadata.

The reference path hard-codes the producer as `COMPOSER`; callers cannot relabel another producer as COMPOSER by setting a field.

### 2. PREPARE → SIGN → COMMIT

`AuthoritativeCommitService.prepare()` reads the current authoritative HEAD and creates a `CommitIntent` containing:

- the exact next epoch;
- the exact predecessor bundle hash;
- the exact predecessor commit-record hash;
- the complete governance context;
- the governance-context SHA-256;
- the COMPOSER change identity.

`CommitIntent.signing_bytes()` is the only material that needs to cross to an HSM/KMS/offline signer.

The VINCULUM commit service does **not** need the root private key.

```text
COMPOSER change
      ↓
PREPARE exact intent
      ↓
external root signer / HSM / KMS
      ↓
SIGNATURE ONLY
      ↓
COMMIT if HEAD is unchanged
```

If another commit wins between PREPARE and COMMIT, the stale intent is rejected.

### 3. Append-only authoritative repository

`FileAuthoritativeStateStore` is the reference implementation of the authoritative state repository.

It maintains:

```text
deployment marker
HEAD
commits/
  epoch-1 immutable commit record
  epoch-2 immutable commit record
  ...
```

Each commit record contains the complete root-signed governance bundle and its COMPOSER change identity. Records and HEAD are HMAC-protected, atomically written, fsynced, and positively read back.

The commit record is written before HEAD moves. A crash can therefore leave an unreachable orphan record, but cannot make a partially written record authoritative.

### 4. Complete history verification

`verify_chain()` validates the reachable history from genesis through current HEAD:

- HMAC integrity;
- record SHA-256;
- Ed25519 root signature;
- deployment/root identity;
- epoch continuity;
- predecessor commit continuity;
- predecessor bundle continuity;
- COMPOSER change metadata;
- commit-intent reconstruction.

`AuthoritativeGovernanceRuntime` verifies the chain on read by default.

### 5. Read-only authoritative runtime

`AuthoritativeGovernanceRuntime` intentionally exposes no:

```text
commit()
advance()
bootstrap()
set_root()
```

Normal decision code can read the authoritative state. It cannot create or advance it.

### 6. Authoritative binding

`VinculumEngine.bind_authoritative()` does not accept a caller-selected `GovernanceContext` or caller-supplied signed bundle.

It re-reads the COMPOSER authoritative repository through `AuthoritativeGovernanceRuntime` and returns an `AuthoritativeBinding`:

```text
BindingReport
+ TrustReceipt
+ AuthoritativeCommitReceipt
```

A valid but **uncommitted** root-signed bundle cannot drive this path.

### 7. CERPA handoff with freshness guard

`CerpaBridge.prepare_review()` converts an `AuthoritativeBinding` into a tamper-evident `CerpaHandoff` for **REVIEW**.

Immediately before CERPA performs its own APPLY, `validate_apply_guard()` re-reads the authoritative repository and rejects the handoff if COMPOSER state changed after VINCULUM bounded the candidate.

VINCULUM does **not** perform CERPA APPLY.

```text
COMPOSER HEAD @ epoch N
        ↓
VINCULUM binding
        ↓
CERPA REVIEW
        ↓
re-read COMPOSER HEAD
        │
        ├─ still epoch N → APPLY_GUARD current
        └─ changed       → STALE_AUTHORITATIVE_STATE
```

---

## Core invariants

1. **Unknown is not pass.**
2. **Hard deterministic failure rejects.**
3. **Governance failure rejects.**
4. **Missing required governance remains unresolved.**
5. **Soft constraints do not authorize.**
6. **A bound requires a hard boundary by default.**
7. **Evidence is content-addressed.**
8. **Provenance must close without cycles or missing parents.**
9. **Authority is action- and scope-specific.**
10. **Governance is not treated as pseudo-probability.**
11. **The root is immutable inside trusted runtimes.**
12. **Loss/corruption of initialized trust state fails closed.**
13. **Epoch rollback and skipping are rejected.**
14. **A new governance bundle must supersede the exact current bundle hash.**
15. **A v0.4 commit must also supersede the exact current commit-record hash.**
16. **PREPARE does not reserve authority; stale intents fail at COMMIT.**
17. **A signed-but-uncommitted bundle is not authoritative.**
18. **The authoritative runtime is read-only.**
19. **The authoritative repository history must be complete and internally consistent.**
20. **CERPA review/apply handoff must still point to the current authoritative state.**
21. **VINCULUM may validate authority; it does not originate human/enterprise authority.**

---

## Install

```bash
python -m pip install vinculum_pylib-0.4.0-py3-none-any.whl
```

Runtime dependency:

```text
cryptography >= 43
```

VINCULUM uses `cryptography` for Ed25519 rather than shipping custom signature primitives.

---

## Authoritative example

See [`examples/authoritative.py`](examples/authoritative.py).

The essential shape is:

```python
bootstrap = AuthoritativeBootstrapService(root=root, store=store)
intent = bootstrap.prepare_genesis(change=change, context=context)

# Production: HSM/KMS/offline signer signs these exact bytes.
signature_b64 = signer(intent.signing_bytes())
bootstrap.commit_genesis(intent=intent, signature_b64=signature_b64)

runtime = AuthoritativeGovernanceRuntime(root=root, store=store)

binding = VinculumEngine(
    governance_policy=GovernancePolicy.authoritative()
).bind_authoritative(hypotheses, constraints, runtime=runtime)

handoff = CerpaBridge().prepare_review(
    binding=binding,
    runtime=runtime,
    episode_id="CERPA-EP-1",
    claim_id="CLAIM-1",
)
```

---

## Deep Sigma placement

```text
RESONATOR
  discovers/tests semantic constraints
          ↓
COMPOSER
  authors and governs the clause/rule state
          ↓
AUTHORITATIVE COMMIT SERVICE
  PREPARE → external SIGN → COMMIT
          ↓
APPEND-ONLY AUTHORITATIVE STATE
          ↓
VINCULUM
  P + D + G against current committed state
          ↓
BOUNDED COHERENCE
          ↓
CERPA
  Claim → Event → Review → Patch → Apply
```

The responsibility rule is:

> **RESONATOR may discover a rule. COMPOSER may publish the authoritative rule. VINCULUM may bind against only the committed rule. CERPA governs what happens next.**

---

## Deliberate boundary

v0.4 proves an enforceable reference path **inside this library**. It does not prove that an external DOC COMPOSER application has no separate database/API/commit route unless that application is actually wired so every authoritative mutation uses this service.

That external integration requirement is explicit rather than implied.

Production must also provide outside the candidate-side application:

- root public-key provisioning;
- protected root private signing key / HSM / KMS policy;
- authoritative repository access control;
- integrity-key or equivalent repository integrity protection;
- durable backup/recovery and operational separation of duties;
- the actual DOC COMPOSER single-commit routing rule;
- CERPA's human/enterprise APPLY authority.

See [`AUTHORITATIVE_CHOKE_POINT.md`](AUTHORITATIVE_CHOKE_POINT.md), [`TRUST_BOUNDARY.md`](TRUST_BOUNDARY.md), and [`CERPA_HANDOFF.md`](CERPA_HANDOFF.md).

---

## Compatibility

v0.4 retains:

- `bind()` — v0.1-compatible analysis path;
- v0.2 evidence/provenance/authority governance;
- `bind_trusted()` and the v0.3 `TrustedGovernanceRuntime` path;
- the v0.3 trusted-governance bundle schema.

`bind_authoritative()` is a new, stricter path. Existing integrations are not silently promoted to authoritative status.

## Validation

The complete v0.1-v0.3 regression suite plus v0.4 authoritative-choke-point and CERPA freshness tests are recorded in [`VALIDATION.md`](VALIDATION.md).
