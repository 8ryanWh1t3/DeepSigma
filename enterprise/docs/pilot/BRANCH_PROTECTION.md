# Branch Protection (Pilot Requirement)

To make CI real, require GitHub checks.

## Required checks
- `Coherence Pilot CI / coherence-ci`

## Settings
GitHub -> Settings -> Branches -> Branch protection rules:
- Require a pull request before merging: enabled
- Require status checks to pass before merging: enabled
- Select required checks: `Coherence Pilot CI / coherence-ci`
- Require conversation resolution: enabled (optional but recommended)

## Result
No one can merge drift without passing Coherence CI.
