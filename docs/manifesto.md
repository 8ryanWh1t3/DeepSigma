# The Reference Layer Manifesto

## Three Failures That Break Autonomous Systems

### 1. Decision Amnesia

Agents act, but nothing remembers why. A model quarantines an account,
escalates a ticket, or approves a trade. Seconds later the reasoning is
gone. When an auditor asks "why did the system do that?" the answer is
silence.

### 2. Authority Vacuum

No one can prove who authorized the action. The agent had a policy. The
policy came from somewhere. But the chain from human intent to machine
execution is undocumented, unverifiable, and invisible.

### 3. Silent Drift

The system changes behavior and nobody notices. Confidence shifts,
outcome distributions rotate, new failure modes emerge. Without
continuous measurement the first sign of drift is a production incident.

---

## What a Reference Layer Does

A reference layer sits between the agent runtime and the outside world.
Every decision passes through four artifacts:

1. **Episode Sealing** -- each decision is captured as a sealed episode
   with cryptographic hash, timestamp, actor, actions, outcome, and
   verification result. The Decision Log Record (DLR) is append-only
   and tamper-evident.

2. **Authority Binding** -- an authority ledger records who granted
   permission for each class of action. Claims are blessed by named
   authority sources with explicit scope and expiry. Proof of authority
   is retrievable for any claim at any time.

3. **Drift Detection** -- runtime signals (outcome changes, confidence
   shifts, decision-type mutations) are captured as typed drift events
   with severity, fingerprint, and recommended patch type. A drift
   density metric tracks signal-to-episode ratio continuously.

4. **Claim Lifecycle** -- atomic claims flow through validation,
   authority check, graph recording, and drift signal emission in a
   single pipeline. Contradictions, expired claims, and unauthorized
   assertions are caught before they reach memory.

---

## Proof

Baseline coherence score from a three-episode demo session:

```json
{
  "overall_score": 90.0,
  "grade": "A",
  "dimensions": [
    {"name": "policy_adherence",    "score": 100.0, "weight": 0.25},
    {"name": "outcome_health",      "score": 66.67, "weight": 0.30},
    {"name": "drift_control",       "score": 100.0, "weight": 0.25},
    {"name": "memory_completeness", "score": 100.0, "weight": 0.20}
  ]
}
```

Four-metric observability output from `coherence metrics`:

```json
{
  "metrics": [
    {"name": "coherence_score",     "value": 90.0,  "unit": "score"},
    {"name": "drift_density",       "value": 0.0,   "unit": "ratio"},
    {"name": "authority_coverage",  "value": 1.0,   "unit": "ratio"},
    {"name": "memory_coverage",     "value": 1.0,   "unit": "ratio"}
  ]
}
```

After injecting drift (outcome change + confidence shift):

```json
{
  "overall_score": 85.75,
  "grade": "B"
}
```

The score dropped, the grade changed, and the drift signals are
queryable. Nothing was lost. Nothing was silent.

---

## The Contract

1. **Intent is explicit.** Every decision records what the agent planned
   to do and why.

2. **Authority is verified.** Every claim traces back to a named grant
   with scope, source, and expiry.

3. **Logic is auditable.** The full provenance chain -- episode, actor,
   actions, outcome, seal -- is retrievable for any decision at any time.

4. **Outcomes are sealed.** Cryptographic hashes bind the decision record
   to its content. Tampering breaks the chain.

This is the reference layer contract. Systems that implement it are
observable, auditable, and governable. Systems that do not are guessing.
