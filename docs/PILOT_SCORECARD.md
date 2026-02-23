# Pilot Scorecard (v2.0.4 GitHub-Native)

Pass/fail criteria for pilot release gate:

- [ ] CI >= 90 in green state
- [ ] Demonstrate CI drop below 75 when assumption expires and drift is open
- [ ] Demonstrate patch restores CI >= 90
- [ ] Demonstrate WHY retrieval by link traversal in <= 60 seconds

## Demo method

1. Green baseline:
   - Run `python3 scripts/compute_ci.py`
   - Confirm report status PASS and CI >= 90.

2. Drift failure simulation:
   - Mark `pilot/drift/DRIFT-2026-001.md` status as `Open`.
   - Remove drift link from `pilot/patches/PATCH-2026-001.md`.
   - Run `python3 scripts/compute_ci.py` and confirm CI < 75.

3. Recovery:
   - Restore drift status to `Closed`.
   - Restore drift link in patch file.
   - Run `python3 scripts/compute_ci.py` and confirm CI >= 90.

4. WHY retrieval KPI:
   - Traverse links in order described in `pilot/README.md`.
   - Confirm median retrieval time <= 60 seconds over repeated runs.
