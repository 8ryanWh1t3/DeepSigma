# DeepSigma KPI Governance

> How KPIs are defined, changed, and trusted.

**Version:** 1.0
**Overlay:** [kpi_standards_overlay.md](./kpi_standards_overlay.md)
**Contract files:** [kpi_contracts/](./kpi_contracts/)

---

## Definitions

**KPI Contract** — A single source-of-truth file per KPI containing: definition, formula, data sources, cadence, thresholds, failure modes, and owner. Stored in `docs/kpi_contracts/<kpi_slug>.md`.

**Overlay** — Mappings from KPIs to external standards (DORA, ISO/IEC 25010, OTel, SMART). The overlay interprets existing numbers through additional lenses. It does not change any formula, threshold, or score.

**KPI_ID** — Stable identifier for a KPI (e.g., `DS-KPI-001`). Never reused.

**KPI_VERSION** — Semantic version per contract (e.g., `1.0`). Bumped on any formula or threshold change.

---

## Change Control

### No Silent Rewrites

A KPI formula, threshold, data source, or cadence must never be changed without a tracked update to both:
1. The KPI contract file (`docs/kpi_contracts/<kpi_slug>.md`)
2. The standards overlay (`docs/kpi_standards_overlay.md`)

### Formula Change Process

Any change to a KPI formula or threshold requires:

| Step | Action | Artifact |
|------|--------|----------|
| 1 | Open PR updating the KPI contract and overlay | PR description references KPI_ID |
| 2 | Bump `KPI_VERSION` in the contract file | e.g., 1.0 → 2.0 |
| 3 | Parallel-run old formula vs new formula for **2 releases** | Both values published in release KPI output |
| 4 | Publish delta notes explaining rationale and numeric impact | Section in PR body or release notes |
| 5 | After parallel-run, retire old formula with a final deprecation note | Contract file updated |

### What Counts as a Change

| Change type | Requires full process? |
|-------------|----------------------|
| Formula modification | Yes |
| Threshold adjustment (floor, max_drop, green/yellow/red) | Yes |
| Data source path change | Yes |
| Cadence change | Yes |
| Cosmetic label or description edit | No — PR only, no version bump |
| Overlay mapping update (DORA, ISO, OTel, SMART) | No — PR only, no version bump |
| Adding a new KPI | Yes (new contract file, overlay row, version 1.0) |
| Retiring a KPI | Yes (mark contract RETIRED, remove from overlay active table) |

---

## Evidence Policy

### Reproducibility Requirement

Every KPI value published in a release must be reproducible from repo artifacts and CI outputs. Specifically:

1. The computation script must exist in the repo.
2. The data sources (files, CI logs, benchmark outputs) must be committed or CI-archived.
3. Running the computation script on the same inputs must produce the same score (±0.01 for floating-point tolerance).

### Experimental KPIs

If a KPI cannot currently be reproduced from artifacts — for example, because it depends on a manual assessment without documented evidence files — it must be labeled **"Experimental"** in:
- The contract file (`status: experimental`)
- The overlay table (Notes column)
- The KPI gate report

Experimental KPIs:
- Are published but do not block releases.
- Must have a remediation plan with a target date for achieving reproducibility.
- Are reviewed every release for promotion to "Active" status.

### Eligibility Tiers

KPI scores are capped by evidence tier (defined in `enterprise/governance/kpi_eligibility.json`):

| Tier | Max Score | Confidence | Requirement |
|------|-----------|------------|-------------|
| unverified | 3.0 | 30% | Basic checks exist |
| simulated | 6.0 | 45% | Simulated workload evidence |
| real | 8.5 | 70% | Real workload evidence |
| production | 10.0 | 90% | Production-level evidence + gates |

---

## Review Roles

| Role | Responsibility |
|------|---------------|
| **Maintainer (DRI)** | Owns KPI definitions, computes values, publishes results. Accountable for accuracy. |
| **Reviewer** | Reviews PRs that modify contracts or overlay. Checks formula correctness, SMART compliance, and mapping defensibility. |
| **Approver** | Final sign-off on formula changes. Must approve any KPI_VERSION bump. For security-related KPIs, approver must have security domain expertise. |

### Escalation

If Reviewer and Maintainer disagree on a formula change, the Approver decides. If the dispute involves a DORA or ISO mapping, the Approver should document the rationale in the PR.

---

## Minimum Bar

Every KPI in the active set must:

1. **Pass SMART** — all five letters (Specific, Measurable, Actionable, Reproducible, Time-bounded) must pass.
2. **Have a contract file** in `docs/kpi_contracts/`.
3. **Have an overlay row** in `docs/kpi_standards_overlay.md`.
4. **Be computable from artifacts** — either automated (telemetry source) or manual with documented evidence files.

If a KPI fails any of these, it is downgraded to Experimental status with a remediation plan filed as a GitHub issue.

---

## Audit Cadence

| Activity | Frequency |
|----------|-----------|
| KPI values computed and published | Every release |
| SMART compliance check | Every release (automated via overlay summary) |
| Full contract review | Quarterly or after any major architecture change |
| Overlay mapping review | Annually or when referenced standard is updated |
| Experimental KPI remediation review | Every release |

---

## Version History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-01 | 1.0 | Initial governance framework |
