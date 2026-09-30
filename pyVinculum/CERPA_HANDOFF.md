# VINCULUM v0.4 — CERPA Handoff

## Purpose

VINCULUM decides whether a probabilistic candidate survives deterministic and governance boundaries.

It does **not** own CERPA APPLY authority.

The v0.4 bridge therefore produces a bounded, replayable handoff rather than performing an action.

## Review handoff

`CerpaBridge.prepare_review()` requires an `AuthoritativeBinding` and re-checks that its COMPOSER commit is still current.

The resulting `CerpaHandoff` contains:

```text
CERPA episode ID
claim ID
phase = REVIEW
AuthoritativeBinding SHA-256
BindingReport SHA-256
AuthoritativeCommitReceipt SHA-256
commit-record SHA-256
bundle SHA-256
governance-context SHA-256
best-supported hypothesis ID
all result states
```

## Apply guard

Immediately before CERPA's own APPLY:

```python
bridge.validate_apply_guard(
    handoff=handoff,
    binding=binding,
    runtime=runtime,
)
```

re-reads the authoritative repository.

If COMPOSER has moved since the binding:

```text
STALE_AUTHORITATIVE_STATE
```

is raised.

If state is still exact, a new envelope is returned with:

```text
phase = APPLY_GUARD
metadata.apply_guard = CURRENT
```

That is permission to continue CERPA's own governance process—not an automatic apply command.

## Why the second check matters

Without it:

```text
VINCULUM evaluates policy revision 17
       ↓
policy revision 18 becomes authoritative
       ↓
CERPA applies an action justified by revision 17
```

v0.4 makes that stale-state transition visible and fail-closed.
