---
title: "Release Verification Checklist — v0.3.0"
version: "0.3.0"
date: "2026-02-16"
---

# v0.3.0 Release Verification Checklist

Run these steps locally before tagging the release.

## 1. Money Demo

```bash
python -m coherence_ops.examples.drift_patch_cycle
```

Expected output:

```
BASELINE  90.00 (A)
DRIFT    85.75 (B)   red=1
PATCH    90.00 (A)   patch=RETCON  drift_resolved=true
Artifacts: examples/demo-stack/drift_patch_cycle_run/
✅ All contract checks passed.
```

## 2. Test Suite

```bash
pytest -q
```

Expected: all tests pass (including 16 Money Demo contract tests).

## 3. Artifacts

```bash
ls examples/demo-stack/drift_patch_cycle_run/
```

Expected files (8):

```
report_baseline.json
report_drift.json
report_after.json
memory_graph_before.json
memory_graph_drift.json
memory_graph_after.json
memory_graph_diff.json
loop.mmd
```

## 4. Diff Integrity

```bash
python -c "
import json
d = json.load(open('examples/demo-stack/drift_patch_cycle_run/memory_graph_diff.json'))
assert 'patch-cycle-001' in d['added_nodes'], 'patch node missing'
assert any(e[1] == 'resolved_by' for e in d['added_edges']), 'resolved_by edge missing'
print('Diff integrity OK')
"
```

## 5. Version Check

```bash
python -c "import coherence_ops; print(coherence_ops.__version__)"
# Expected: 0.3.0

grep 'version' pyproject.toml | head -1
# Expected: version = "0.3.0"
```

## 6. Tag and Push (do not run until all checks pass)

```bash
git tag -a v0.3.0 -m "v0.3.0 — Living Memory: Drift→Patch in one command"
git push origin main --tags
```

Then create the GitHub release at:
`https://github.com/8ryanWh1t3/DeepSigma/releases/new?tag=v0.3.0`

Use `release/RELEASE_NOTES_v0.3.0.md` as the release body.
