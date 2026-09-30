# VINCULUM pyLib v0.4.0 — Validation Record

## Source test suite

Command:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Result:

```text
69 tests
69 PASS
0 FAIL
0 ERROR
```

Coverage includes the complete v0.1-v0.3 regression suite plus v0.4 authoritative integration tests.

## v0.4 authoritative controls exercised

The v0.4 tests explicitly verify:

- genesis requires the deployment-only bootstrap service;
- normal commit service cannot create genesis;
- authoritative runtime exposes no commit/advance/bootstrap/root-setter path;
- PREPARE fixes exact predecessor state;
- concurrent/stale intent loses at COMMIT;
- signature must cover the exact prepared intent;
- invalid root signature cannot publish genesis;
- HEAD deletion fails closed;
- HEAD integrity tamper fails closed;
- commit-record integrity tamper fails closed;
- signed-but-uncommitted state cannot drive authoritative binding;
- complete authoritative history verifies from genesis to HEAD;
- missing predecessor history makes the authoritative runtime fail closed;
- commit record is durable before HEAD moves;
- simulated crash/failure during HEAD move leaves previous HEAD authoritative;
- authoritative binding uses repository context, not caller context;
- authoritative binding requires the read-only authoritative runtime type;
- CERPA REVIEW handoff binds to the current authoritative commit;
- tampered CERPA handoff content is rejected;
- CERPA APPLY guard rejects state that changed after VINCULUM binding.

## Core semantic regression

v0.3 semantic-bearing modules and core engine functions were hash-compared to v0.4.

The original implementations of:

```text
VinculumEngine.bind
VinculumEngine.bind_trusted
VinculumEngine._bind_one
GovernancePolicy.compatibility
GovernancePolicy.strict
GovernancePolicy.trusted
```

are byte-identical at the function-body level.

See `SEMANTIC_DELTA.md` for hashes.

## Python syntax/bytecode compilation

```text
src/      PASS
examples/ PASS
tests/    PASS
```

## Wheel build

The wheel was built locally with build isolation disabled because the execution environment has no outbound package-index access:

```bash
python -m pip wheel . --no-deps --no-build-isolation -w dist
```

Result:

```text
vinculum_pylib-0.4.0-py3-none-any.whl
SHA-256: 53f6641fc3e48b9a3278295d51cd52a02e31c0ff65d1a1499879bbf28964af6a
```

## Installed-wheel validation

A separate virtual environment was created, the generated wheel was installed, and the tests were run outside the source tree.

Result:

```text
imported version: 0.4.0
import source: site-packages/vinculum/__init__.py
69 tests
69 PASS
0 FAIL
0 ERROR
```

The authoritative example was then executed against the installed wheel and produced:

```text
BOUNDED_ACCEPTED
CERPA phase = APPLY_GUARD
```

## Deliberate limitations

This validation proves the pyLib reference path. It does not prove that an external DOC COMPOSER product has removed every alternate mutation route. That requires an integration test against the actual Composer authoritative runtime/repository.

Likewise, `CerpaBridge` validates the handoff/freshness boundary; it does not claim to execute CERPA's downstream human/enterprise APPLY authority.

## Delivered-archive verification

The release ZIP was extracted into a new directory and validated from the extracted bytes:

```text
MANIFEST.sha256: 40 / 40 files verified
Source tests:      69 / 69 PASS
Authoritative demo: BOUNDED_ACCEPTED
CERPA guard:        APPLY_GUARD
ZIP integrity:      no compressed-data errors
```
