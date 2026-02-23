# Coherence Ops Pilot Contract (1 page)

## Objective
Prove mechanically reconstructable institutional memory under adversarial review.

## Deliverables
- PASS→FAIL→PASS drill (`make pilot-in-a-box`)
- CI report on every PR (`pilot/reports/ci_report.*`)
- Repo-native DLR/Assumption/Drift/Patch workflow with DRI model

## Success metrics (minimum)
- 2 new users complete WHY-60s challenge
- CI gate blocks a bad merge at least once (recorded)
- 1 drift → patch cycle completed in < 7 days

## Non-goals (explicit)
- Enterprise SSO/RBAC
- Production connector SLAs
- “No-code integration” promises
