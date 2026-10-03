# Compatibility and provenance

## Source actually inspected

Repository: `8ryanWh1t3/DeepSigma`  
Commit: `6c4dd7ebacda4c3eb2cb505224c28348410bd05e`  
Directory: `vinculum-pylib-v0.7.0/`

The connector exposed `pipeline.py`, `serialization.py`, and the relevant portions
of `core.py` and `matrix.py`. The baseline snapshot IDs and source blob identifiers
are retained in `BASELINE.json`. No base-library source is redistributed here.

The readable Library migration notes and the GitHub source use different job
configuration spellings under the same 0.7.0 version label. Library notes refer
to `vinculum.pipeline/1`; the inspected executable GitHub source uses
`vinculum.pipeline.job/1`. This package does not silently reconcile those builds.
The adapter accepts the following result contract from the inspected source:

```
run.to_dict().schema                    vinculum.pipeline.result/1
run.to_dict().engine_version            0.7.0
run.scenario.to_dict().schema           vinculum.crossorder.scenario/1
run.to_dict().report.schema             vinculum.crossorder.report/1
run.to_dict().report.engine_version     0.7.0
```

The adapter reads results, not job configuration. A future or alternate version
with another result schema fails explicitly. A shared version string alone does
not establish compatibility; run the real-host test on the intended build.

## What was tested

The add-on's behavior, serialization round trips, four-lens constraints, explicit
scope-expansion rule, traversal/back/replay, cross-episode targets, exact numeric
preservation, read-only inspection, SQLite restart/corruption/rollback cases,
non-overwriting exports, projection verification and CLI were exercised locally.
Adapter tests use a clearly marked synthetic fixture shaped to the inspected
serialization API. They preserve all five host statuses and prove the fixture is
not mutated or re-evaluated.

## What was not tested

The available Library ZIP/wheel materialization returned an unavailable authorized
raw-byte path. Direct source download into the container also failed. Consequently
the actual VINCULUM host distribution was not installed here. The included real
host test is explicitly skipped in this environment. Its success and the base
library's full regression suite remain necessary integration gates.

No automatic GitHub or Library write, version bump, branch creation, deployment,
PyPI publication, host UI wiring or original-engine modification occurred.
