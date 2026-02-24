# Verifiers

A **Verifier** is a postcondition check that runs after an action is dispatched to confirm the action had the intended effect — or to detect and report failure safely. The governing principle is: **success means verified.**

Verifiers are defined per `decisionType` in the DTE (`verification.methods`) and triggered by the supervisor scaffold after the action stage. A verifier returns one of three outcomes:

| Outcome | Meaning |
|---------|---------|
| `pass` | Postcondition satisfied — episode proceeds to seal |
| `fail` | Postcondition not satisfied — supervisor emits drift, may trigger degrade |
| `inconclusive` | Could not determine outcome (timeout, missing data) — treated as `fail` for safety |

---

## Included Scaffolds

### `read_after_write`

Re-reads the target resource immediately after the action and asserts that the mutation is visible.

**Use when:** the action writes a value that should be immediately readable back (e.g., update a flag, set a status, write a record).

**Checks:** the value read back matches the expected post-action state within `verifyTimeoutMs`.

**Emits drift:** `verify` signal with severity `yellow` if the read-back fails, `red` if it times out.

### `invariant_check`

Evaluates a boolean condition on system state without referencing the specific target resource.

**Use when:** the action is expected to satisfy a global or cross-resource invariant (e.g., "no account with balance < 0 after transfer", "service health endpoint returns 200").

**Checks:** the callable condition returns `True` within `verifyTimeoutMs`.

**Emits drift:** `verify` signal with severity `yellow` if the condition is `False`, `red` on timeout.

---

## Implementing a Custom Verifier

Place the verifier in the `verifiers/` directory. A verifier is any callable that accepts an episode context dict and returns a `VerificationResult`:

```python
# verifiers/my_verifier.py
from engine.verifier_base import VerificationResult

def verify(context: dict) -> VerificationResult:
    target_id = context["action"]["targetRefs"][0]["id"]
    # ... check the resource
    ok = fetch_status(target_id) == "active"
    return VerificationResult(
        outcome="pass" if ok else "fail",
        detail=f"Status check for {target_id}: {'ok' if ok else 'failed'}",
    )
```

Register the verifier identifier in the DTE:

```json
"verification": {
  "requiredAboveBlastRadius": "small",
  "methods": ["my_verifier"],
  "verifyTimeoutMs": 5000
}
```

---

## Relationship to Other Contracts

- Verification requirements are set in the **[DTE Schema](DTE-Schema)** (`verification.requiredAboveBlastRadius`, `methods`, `verifyTimeoutMs`)
- A verifier `fail` or `inconclusive` result causes the supervisor to emit a `verify` **[Drift Event](Drift-Schema)**
- Verifier outcomes are recorded in the sealed **[Episode Schema](Episode-Schema)** under the `verification` field

---

## Related Pages

- [Contracts](Contracts) — overview of all four contract types
- [DTE Schema](DTE-Schema) — where verification requirements are configured
- [Drift Schema](Drift-Schema) — `verify` drift type
- [Degrade Ladder](Degrade-Ladder) — verifier failure can trigger degrade steps
