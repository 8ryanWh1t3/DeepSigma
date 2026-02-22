# Issue War Plan (Build 77)

## Objective
Convert the current 33 open issues into a deterministic execution sequence that maximizes KPI lift and pilot credibility.

## Current Topology
- Open issues: 33
- KPI pressure points:
  - `automation_depth`: 12 open (6x P0, 5x P1, 1x P2)
  - `scalability`: 10 open (10x P1)
  - `enterprise_readiness`: 4 open (4x P1)
  - `data_integration`: 2 open (2x P1)
  - `economic_measurability`: 2 open (1x P1, 1x P2)
  - `operational_maturity`: 3 open (1x P1, 2x P2)
  - `technical_completeness`: 0 open
  - `authority_modeling`: 0 open

## Non-Negotiable Constraint
`automation_depth` is capped at `6.0` while any `sev:P0` issue remains open in that KPI portfolio (`p0_open_cap: 6.0`).

## Milestones
- `M1: Pilot Uncap` (clear automation P0s + proof loop foundations)
- `M2: Pilot Pack + Publish` (demo + evidence + release posture)
- `M3: Scale v2.1` (mesh/multi-region/k8s scale program)

## Lane 1: Uncap the Radar (72h)
Goal: remove cap on `automation_depth` by clearing P0 blockers.

Issues:
- #186 Release Pipeline Epic (umbrella, checklist owner)
- #134 Dependency lock + deterministic install
- #137 CI release hygiene: test + lint + tag -> artifacts
- #150 Signed releases with Sigstore + SBOM
- #151 Publish to PyPI + GHCR on tagged release
- #147 Envelope-level encryption for evidence at rest

Rules:
- Keep #186 as canonical umbrella.
- Convert sibling items into linked checklist/sub-issues under #186.
- Do not create duplicate P0s for the same release control surface.

Expected KPI effect:
- `automation_depth`: uncap from 6.0 to baseline trajectory (7.0+ on next valid run if debt/overdue penalties are controlled).

## Lane 2: Pilot Proof Loop
Goal: make the pilot indisputable under procurement and technical review.

Issues:
- #133 One-command Money Demo
- #144 Automated golden path proof regeneration in CI
- #135 Golden-path proof artifacts in README
- #199 Pilot Results doc (PASS->FAIL->PASS evidence)

Expected output:
- Deterministic demo command path.
- Auto-regenerated proof artifacts in CI.
- README evidence links that work from fresh clone.
- Final pilot results page for stakeholder review.

Expected KPI effect:
- `economic_measurability` up from low baseline.
- `operational_maturity` and `automation_depth` improved through proof automation and visible artifacts.

## Lane 3: Scale Credibility (Pilot-safe scope)
Goal: show believable scale without expanding to full multi-region program in pilot.

Pilot-grade minimum:
- #195 Stateless API split: remove in-memory runtime state
- #145 Data retention automation: TTL purge + compaction cron
- #197 Load testing and scaling guide

Defer to `M3` (v2.1 scale program):
- #149 Multi-region mesh epic
- #152 Horizontal scaling epic
- #191, #192, #193, #194 mesh internals
- #189 HPA/production overlay expansion

Expected KPI effect:
- `scalability` rises via concrete pilot-ready controls and docs.
- Reduced execution risk by deferring deep mesh internals.

## 7-Day Closure Sequence
Day 1:
- Close #134, #137

Day 2:
- Close #150, #151

Day 3:
- Resolve/close #147
- Close #186 when all linked blockers are complete

Day 4:
- Close #144

Day 5:
- Close #135

Day 6:
- Close #133

Day 7:
- Close #195, #145, #197
- Regenerate KPI artifacts and publish status snapshot

## Severity/Label Governance
- Keep `sev:P0` only for hard blockers:
  - release integrity
  - determinism
  - publish integrity
  - baseline security controls
- Move mesh-heavy forward-looking work to `sev:P2` under `M3` unless actively shipping this sprint.

## KPI Impact Expectations (by release)
- Next release after P0 clear:
  - `automation_depth` uncap event; score should move above cap-constrained state.
- Next release after proof loop closures:
  - `economic_measurability` and `operational_maturity` visibly improve.
- Next release after pilot-grade scale closures:
  - `scalability` increases with lower execution noise than mesh-first approach.

## Execution Checkpoint Commands
```bash
make issues-review
make issue-label-gate
make kpi
```

## Exit Criteria
- No open `sev:P0` in `kpi:automation_depth`.
- PASS->FAIL->PASS proof path is runnable from docs.
- KPI composite compares at least two releases with valid deltas.
- Pilot package is review-ready for external stakeholders.
