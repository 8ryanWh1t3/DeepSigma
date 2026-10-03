# VINCULUM Folding Add-on v0.1.0 — Validation

## Measured results

| Gate | Result |
|---|---|
| Source tests | **154 passed, 0 failed, 1 skipped** |
| Installed-wheel tests, imported outside source tree | **154 passed, 0 failed, 1 skipped** |
| Installed code equals packaged source | PASS |
| Installed console demo and bundle verification | PASS |
| Python 3.10 syntax parsing, 10 source modules | PASS; runtime not exercised |
| Actual execution environment | Python 3.13.5, Linux |
| Wheel version / distribution / module identity | 0.1.0 / vinculum-folding / vinculum_folding |
| Runtime dependencies | None beyond Python standard library |
| Original host code modified | No |
| Original host regression suite rerun | **No** |
| Actual host integration test | **SKIPPED, not passed** |

The one skipped case in each run is the same real-host integration test. The
remaining tests include a clearly labeled synthetic host serialization fixture.
The full source-inspected VINCULUM distribution was not available to install.
This is not an end-to-end production integration or release lock.

## Exercised negative controls

Unknown fields and duplicate IDs/JSON keys; unsupported JIT names; missing lens
attribution/evidence; missing Awareness axes; naive/reversed time; inexact/nonfinite
numbers; dangling references; tampered host captures; omitted/reoriented host
pairs; all five host pair statuses; no invented unpaired scores; stale and forged
traversal trails; unloaded cross-episode targets; capacity bounds; revision gaps;
stale writers; corrupt/missing SQLite files; actual separate-process restart;
rollback checked against an external expected tip; export overwrite refusal;
manifest path injection; symlink and extra-file rejection; recomputed manifest
with an inconsistent read-only projection; CLI success and failure paths.

The rollback test explicitly demonstrates that an internally consistent older
journal cannot be recognized as a rollback without an independently retained tip.
That limit is not hidden behind a successful hash check.

## Evidence files

`validation/source-tests.xml`, `validation/source-tests.txt`,
`validation/wheel-tests.xml`, `validation/wheel-tests.txt`,
`validation/installed-smoke.json`, `validation/wheel-build.txt`,
`validation/wheel-install.txt` and `validation/summary.json`.

Wheel SHA-256:

```text
21f8f7c45d49a8a9d14f6e1800a5f2be9d4cab9d72e2e6c6a3cf898d05809239
```

Run `python scripts/check_host.py /path/to/existing_job.json` after installing the
intended VINCULUM host build. It exits nonzero rather than reporting PASS when
host execution or schema compatibility is unavailable. Then rerun the original
host regression suite separately.
