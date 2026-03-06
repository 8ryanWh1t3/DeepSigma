# What Is AuthorityOps?

## AuthorityOps is NOT access control

Access control asks a binary question: "Can this user access this resource?" The answer is yes or no, evaluated once, with no memory of why.

AuthorityOps asks a different question entirely:

> Can this actor perform this action on this resource, given adequate reasoning, with non-expired assumptions, within blast radius limits, and with a complete decision lineage?

The answer is not binary. It is graduated, dynamic, reasoning-bound, and sealed.

## What AuthorityOps IS

AuthorityOps is the authority enforcement layer of Decision Infrastructure. It binds five things into a single evaluable control plane:

1. **Authority to act** -- who granted this, and is the grant still valid?
2. **Bound to reasoning** -- does a Decision Log Record exist with claims and evidence?
3. **Constrained by assumptions** -- are the assumptions backing this decision still fresh?
4. **Enforced at runtime** -- every action passes through the 11-step evaluation pipeline before execution.
5. **Remembered as evidence** -- every verdict, allow or block, is sealed into a hash-chained audit record.

Nothing proceeds without all five. This is not optional. This is the contract.

## The 6 Verdicts

AuthorityOps produces exactly one of six terminal verdicts for every evaluation:

| Verdict | Meaning |
|---------|---------|
| **ALLOW** | Authority exists, reasoning is present, assumptions are fresh, blast radius is within bounds, kill switch is clear. Proceed. |
| **BLOCK** | Authority check failed. Required fields missing, actor unknown, or policy violation. Do not proceed. |
| **ESCALATE** | Authority may exist but blast radius exceeds policy maximum. Requires human approval before proceeding. |
| **EXPIRED** | Authority existed at some point, but assumptions have gone stale or claim half-lives have decayed. Re-evaluate before proceeding. |
| **MISSING_REASONING** | No Decision Log Record found for this action. Authority cannot be verified without reasoning. Provide a DLR. |
| **KILL_SWITCH_ACTIVE** | System-wide kill switch is active. All autonomous actions are halted regardless of authority. |

Every verdict is final for that evaluation cycle. Every verdict is audited. There is no silent pass-through.

## The Complete Chain

Every action evaluated by AuthorityOps must have a complete chain:

```
WHO       -->  Actor resolved with roles and delegation source
WHY       -->  DLR present with claims, evidence, and confidence scores
WHAT      -->  Assumptions checked for freshness; half-lives within bounds
EVIDENCE  -->  Policy evaluated step-by-step with pass/fail per constraint
WHAT      -->  Sealed audit record with chain hash, assumption snapshot,
HAPPENED        and expiry state
```

If any link is missing, the chain is broken. A broken chain does not produce ALLOW.

## How It Differs from Traditional Access Control

Traditional access control:

- Binary: yes or no
- Static: evaluated once at the gate
- Identity-based: who are you?
- Memoryless: no record of why access was granted
- Assumption-blind: does not know or care if the basis for the decision has changed

AuthorityOps:

- **Graduated**: six verdicts, not two
- **Dynamic**: re-evaluates every time, checking freshness and half-lives
- **Reasoning-bound**: requires a DLR with claims and evidence, not just identity
- **Sealed**: every evaluation produces a hash-chained audit record
- **Time-aware**: assumptions expire, delegations expire, authority decays
- **Blast-radius-scoped**: limits the damage any single action can cause

## The Operating Principle

Every consequential autonomous action must satisfy this contract before execution:

- Intent is explicit (the action request exists with typed fields).
- Authority is verified (the actor has a valid, non-expired grant).
- Reasoning is present (a DLR with claims backs the decision).
- Assumptions are fresh (half-lives have not decayed past threshold).
- Blast radius is bounded (the action scope does not exceed policy limits).
- The outcome is sealed (an immutable audit record is written regardless of verdict).

This is not governance theater. This is the structural guarantee that every autonomous action can be reconstructed, questioned, and proven under adversarial review.
