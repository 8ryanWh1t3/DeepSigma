# Branch Protection (Pilot Requirement)

## Required checks
GitHub → Settings → Branches → Branch protection rules:
- Require a pull request before merging: ✅
- Require status checks to pass before merging: ✅
- Select required checks:
  - `Coherence Pilot CI / coherence-ci` (or your workflow’s exact check name)
- Require conversation resolution: ✅ (recommended)

Result: CI becomes “real” — bad drift cannot merge.
