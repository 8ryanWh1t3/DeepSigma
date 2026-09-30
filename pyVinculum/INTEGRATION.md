# Deep Sigma Integration — VINCULUM v0.4

## Responsibility boundaries

### RESONATOR

Discovers, compares, and tests semantic relationships and candidate deterministic constraints.

### COMPOSER

Authors governed clauses/rules and owns the publication decision that makes a governance state authoritative.

### VINCULUM

Reads the current committed COMPOSER state, evaluates P + D + G under that state, and produces bounded-coherence evidence.

### CERPA

Carries the result through Claim → Event → Review → Patch → Apply under its own human/enterprise authority.

## Full reference chain

```text
RESONATOR finding
       ↓
COMPOSER clause/rule revision
       ↓
ComposerChange
       ↓
PREPARE CommitIntent
       ↓
HSM/KMS/offline root signature
       ↓
COMMIT
       ↓
append-only authoritative state
       ↓
AuthoritativeGovernanceRuntime
       ↓
VinculumEngine.bind_authoritative()
       ↓
AuthoritativeBinding
       ↓
CerpaBridge.prepare_review()
       ↓
CERPA REVIEW
       ↓
CerpaBridge.validate_apply_guard()
       ↓
CERPA APPLY authority
```

## Stable identities that should survive the stack

```text
Clause ID
Constraint ID
Evidence ID
Provenance ID
Authority Grant ID
Governance Context ID
Composer Change ID
Artifact ID
Revision
Deployment ID
Root Key ID
Epoch
Commit Intent SHA-256
Bundle SHA-256
Commit Record SHA-256
Authoritative Commit Receipt SHA-256
Binding Report SHA-256
Authoritative Binding SHA-256
CERPA Episode ID
CERPA Claim ID
CERPA Handoff SHA-256
```

## Full DOC COMPOSER integration gate

Before claiming the external product is fully integrated, prove:

1. Every authoritative mutation routes through one COMPOSER publish/commit service.
2. No direct repository write can create a current authoritative state.
3. The root signer is external to candidate-side application logic.
4. COMPOSER cannot skip epoch/predecessor requirements.
5. VINCULUM authoritative binding reads repository state rather than caller state.
6. CERPA rechecks state immediately before APPLY.
7. Negative tests prove each bypass route fails.

The v0.4 pyLib implements the reference contract for items 3–6 and the internal portion of item 2. Item 1 must be proven in the actual DOC COMPOSER application/runtime.
