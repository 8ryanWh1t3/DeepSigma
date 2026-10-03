# Integration handoff — preserve the host, add the sidecar

1. Install the new wheel next to the intended VINCULUM pyLib build. Do not copy
   its files into the `vinculum` namespace or alter host exports/scoring.
2. Run `python -m pytest -q tests/test_host_integration.py` in that environment.
   A skip or error is not an integration pass. Confirm the accepted schemas in
   COMPATIBILITY.md; the version label alone is insufficient.
3. Run the original host regression suite separately. Retain both reports.
4. After the ordinary pipeline run, call `from_pipeline(run, ...)` and export to
   a distinct directory. Retain the original pipeline job and source artifacts
   for actual host re-execution.
5. Bind `view.json` to the read-only VINCULUM surface. Use episode/revision/node
   identities, the four named lenses and the full original pair result. Do not
   add an APPROVE or APPLY button to the viewer.
6. Route draft changes to Studio. A revision is a new FoldEpisode, not a mutation
   of the prior snapshot. Keep external links version-pinned; never follow an
   implicit latest version.
7. Route `review_input.json` into the host's actual governed review mechanism.
   It is a draft, not an existing CERPA record. DLR/RS/DS/MG records and authority
   must come from their owning systems.
8. Retain an independently protected digest/checkpoint for production integrity.
   The included SQLite journal is not the established Policy Fence trust store.

Acceptance: original host output unchanged; all five pair statuses preserved;
no invented time/grade/coverage; four JIT lenses visible; return path replayable;
source evidence recoverable; inspection never authorizes action.
