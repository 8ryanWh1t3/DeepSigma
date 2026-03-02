# DeepSigma KPI Standards Overlay

> **Purpose:** Same KPIs, additional interpretation layer. This document maps every DeepSigma KPI to four external standards frameworks — DORA, ISO/IEC 25010, OpenTelemetry, and SMART metric hygiene — without changing any formula, threshold, or score.

**Overlay version:** 1.1
**Applicable repo version:** v2.1.0
**Last updated:** 2026-03-01
**Governance:** [kpi_governance.md](./kpi_governance.md)
**Contract files:** [kpi_contracts/](./kpi_contracts/)
**Full TEC Summary:** [TEC_SUMMARY.md](../enterprise/release_kpis/TEC_SUMMARY.md)

---

## How to Read This Table

| Column | Meaning |
|--------|---------|
| **KPI** | Internal identifier |
| **What it measures** | Plain-English intent |
| **Formula** | Pseudo-formula (see contract files for full detail) |
| **Data source** | Repo paths that feed the computation |
| **Cadence** | How often the value is recomputed |
| **DORA** | Mapping to DORA four-key metric, or N/A |
| **ISO 25010** | 1–2 ISO/IEC 25010 quality characteristics |
| **OTel** | Custom metric name following internal `deepsigma.*` convention, or N/A |
| **SMART** | Pass/Fail per letter; net PASS only if all five pass. PASS\* = passes via documented rubric + evidence; see [footnote](#smart-footnotes) |

### Confidence Methodology

Tier confidence (from `kpi_eligibility.json`) is uniform at 0.90 for production tier. The **overlay-adjusted confidence** below varies by measurement type:

| Measurement type | Adjustment | Rationale |
|-----------------|------------|-----------|
| Deterministic artifact checks | 0.97 | Binary file-existence; no interpretation |
| Deterministic counts | 0.95 | File/dir counts; minor path sensitivity |
| CI benchmark (real workload) | 0.92 | Reproducible but runner-variant |
| Manual rubric + evidence files | 0.78 | Repeatable via rubric, but human judgment involved |
| Derived from benchmark + manual | 0.85 | Mixed automated/manual inputs |

---

## Release KPIs (8 Core)

### 1. Technical Completeness

| Field | Value |
|-------|-------|
| **What it measures** | Presence and breadth of core source, tests, CI, and packaging artifacts |
| **Current (v2.1.0)** | **10.0**/10 · Tier: production · Confidence: 97% |
| **Formula** | Points-based: +2 src/core exists, +2 tests/ exists, +2 compute_ci.py present, +2 workflows present, +2 pyproject.toml present; capped at 10 |
| **Data source** | `src/core/`, `tests/`, `enterprise/scripts/compute_ci.py`, `.github/workflows/`, `pyproject.toml` |
| **Cadence** | Every release (CI pipeline via `make kpi`) |
| **Contract** | [kpi_contracts/technical_completeness.md](./kpi_contracts/technical_completeness.md) |
| **DORA** | N/A |
| **ISO 25010** | Maintainability (Modularity), Functional Suitability (Completeness) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 2. Automation Depth

| Field | Value |
|-------|-------|
| **What it measures** | Breadth of CI/CD automation: workflows, scripts, build tooling |
| **Current (v2.1.0)** | **10.0**/10 · Tier: production · Confidence: 95% |
| **Formula** | `(workflow_count × 1.2) + (scripts_count / 30 × 4) + makefile_bonus`; capped at 10 |
| **Data source** | `.github/workflows/*.yml`, `enterprise/scripts/*.py`, `Makefile` |
| **Cadence** | Every release |
| **Contract** | [kpi_contracts/automation_depth.md](./kpi_contracts/automation_depth.md) |
| **DORA** | Deployment Frequency (partial — automation is a prerequisite for high deployment frequency) |
| **ISO 25010** | Maintainability (Testability), Performance Efficiency (Time Behaviour) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 3. Authority Modeling

| Field | Value |
|-------|-------|
| **What it measures** | Strength of cryptographic authority controls: signing, key lifecycle, evidence chain |
| **Current (v2.1.0)** | **10.0**/10 · Tier: production · Confidence: 78% · Signing: HMAC |
| **Formula** | Manual rubric backed by evidence artifacts; scored 0–10 |
| **Data source** | `enterprise/release_kpis/security_metrics.json`, `enterprise/release_kpis/authority_evidence.json`, `docs/KEY_LIFECYCLE.md` |
| **Cadence** | Every release |
| **Contract** | [kpi_contracts/authority_modeling.md](./kpi_contracts/authority_modeling.md) |
| **DORA** | N/A |
| **ISO 25010** | Security (Accountability, Authenticity), Reliability (Fault Tolerance) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS\* · T:PASS · **Net: PASS\*** |
| **Notes** | Source is "manual." Repeatable via documented rubric + evidence files; if evidence artifacts are absent, score is capped per eligibility tiers. See [SMART footnotes](#smart-footnotes). |

### 4. Enterprise Readiness

| Field | Value |
|-------|-------|
| **What it measures** | Presence of operational documentation and governance guardrails |
| **Current (v2.1.0)** | **10.0**/10 · Tier: production · Confidence: 97% |
| **Formula** | `clamp(points × 2, 0, 10)` where +1 each: BRANCH_PROTECTION.md, PILOT_CONTRACT_ONEPAGER.md, kpi.yml workflow, kpi_gate.yml workflow, Makefile |
| **Data source** | `BRANCH_PROTECTION.md`, `PILOT_CONTRACT_ONEPAGER.md`, `.github/workflows/kpi.yml`, `.github/workflows/kpi_gate.yml`, `Makefile` |
| **Cadence** | Every release |
| **Contract** | [kpi_contracts/enterprise_readiness.md](./kpi_contracts/enterprise_readiness.md) |
| **DORA** | N/A |
| **ISO 25010** | Compatibility (Co-existence), Usability (Operability) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 5. Scalability

| Field | Value |
|-------|-------|
| **What it measures** | System throughput and recovery performance under load |
| **Current (v2.1.0)** | **10.0**/10 · Tier: production · Confidence: 92% · 3,785,000 RPS · 41,367 MB/min · MTTR 0.026s |
| **Formula** | `2.0 + MTTR_points(0–3) + RPS_points(0–5) + MB_min_points(0–3)`; capped at 10. Full ceiling requires `kpi_eligible=true` and `evidence_level="real_workload"`; otherwise capped at 4.0 |
| **Data source** | `enterprise/release_kpis/scalability_metrics.json`, `enterprise/scripts/reencrypt_benchmark.py` |
| **Cadence** | Every release (benchmark runs in CI) |
| **Contract** | [kpi_contracts/scalability.md](./kpi_contracts/scalability.md) |
| **DORA** | N/A (performance metric, not a DORA key) |
| **ISO 25010** | Performance Efficiency (Time Behaviour, Resource Utilisation, Capacity) |
| **OTel** | Custom gauge: `deepsigma.benchmark.throughput_rps` |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 6. Data Integration

| Field | Value |
|-------|-------|
| **What it measures** | Breadth of connector and schema integration surface |
| **Current (v2.1.0)** | **10.0**/10 · Tier: production · Confidence: 95% |
| **Formula** | `clamp(points × 2, 0, 10)` where +1 per connector directory found + schema/src bonuses |
| **Data source** | `connectors/`, `scripts/connectors/`, `docs/docs/connectors/`, `schemas/`, `src/services/`, `src/demos/` |
| **Cadence** | Every release |
| **Contract** | [kpi_contracts/data_integration.md](./kpi_contracts/data_integration.md) |
| **DORA** | N/A |
| **ISO 25010** | Compatibility (Interoperability), Portability (Adaptability) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 7. Economic Measurability

| Field | Value |
|-------|-------|
| **What it measures** | Ability to quantify cost-per-decision and effort economics |
| **Current (v2.1.0)** | **10.0**/10 · Tier: production · Confidence: 85% · $2,804/decision · $692K total |
| **Formula** | `base(3.0) + MTTR_points(0–3) + RPS_points(0–2) + MB_min_points(0–2)`; capped at 10. Full ceiling requires `kpi_eligible=true` and `evidence_level="real_workload"` |
| **Data source** | `enterprise/release_kpis/economic_metrics.json`, `enterprise/release_kpis/TEC_SUMMARY.md` |
| **Cadence** | Every release |
| **Contract** | [kpi_contracts/economic_measurability.md](./kpi_contracts/economic_measurability.md) |
| **DORA** | N/A |
| **ISO 25010** | Maintainability (Analysability), Functional Suitability (Appropriateness) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS\* · T:PASS · **Net: PASS\*** |
| **Notes** | Benchmark inputs are automated; TEC-derived cost model involves manual assumptions. Repeatable via documented formula; see [SMART footnotes](#smart-footnotes). |

### 8. Operational Maturity

| Field | Value |
|-------|-------|
| **What it measures** | Presence of pilot tooling, reporting infrastructure, and operational runbooks |
| **Current (v2.1.0)** | **10.0**/10 · Tier: production · Confidence: 95% |
| **Formula** | `clamp(points × 1.25, 0, 10)` where +2 pilot_in_a_box.py, +1 why_60s_challenge.py, +2 pilot/reports/, +2 coherence_ci.yml, +1 CI score parse |
| **Data source** | `enterprise/scripts/pilot_in_a_box.py`, `enterprise/scripts/why_60s_challenge.py`, `pilot/reports/`, `.github/workflows/coherence_ci.yml`, `pilot/reports/ci_report.json` |
| **Cadence** | Every release |
| **Contract** | [kpi_contracts/operational_maturity.md](./kpi_contracts/operational_maturity.md) |
| **DORA** | Change Failure Rate (partial — maturity tooling reduces failure rate); MTTR (partial — pilot tooling accelerates recovery) |
| **ISO 25010** | Reliability (Maturity, Availability, Recoverability) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

---

## Coherence Metrics (4 Core)

### 9. Coherence Score

| Field | Value |
|-------|-------|
| **What it measures** | Weighted composite of policy adherence, outcome health, drift control, memory completeness |
| **Current (v2.1.0)** | **90**/100 |
| **Formula** | Weighted sum; 0–100 scale |
| **Data source** | `src/core/metrics.py`, episode data via CLI `coherence metrics` |
| **Cadence** | Per-episode (real-time) + aggregated per release |
| **DORA** | N/A |
| **ISO 25010** | Reliability (Maturity), Functional Suitability (Correctness) |
| **OTel** | Custom gauge: `deepsigma.coherence.score` |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 10. Drift Density

| Field | Value |
|-------|-------|
| **What it measures** | Drift signals per episode; lower is better |
| **Current (v2.1.0)** | **0.0000** |
| **Formula** | `drift_signals / total_episodes`; range 0.0–1.0 |
| **Data source** | `src/core/metrics.py`, episode data |
| **Cadence** | Per-episode + aggregated per release |
| **DORA** | Change Failure Rate (analogous — drift signals indicate unintended divergence from policy) |
| **ISO 25010** | Reliability (Fault Tolerance) |
| **OTel** | Custom gauge: `deepsigma.drift.density` |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 11. Authority Coverage

| Field | Value |
|-------|-------|
| **What it measures** | Fraction of claims backed by a valid authority grant |
| **Current (v2.1.0)** | **1.00** (100%) |
| **Formula** | `valid_grants / total_claims`; range 0.0–1.0 |
| **Data source** | `src/core/metrics.py`, authority ledger |
| **Cadence** | Per-episode + aggregated per release |
| **DORA** | N/A |
| **ISO 25010** | Security (Accountability, Non-repudiation) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 12. Memory Coverage

| Field | Value |
|-------|-------|
| **What it measures** | Fraction of DLR episodes persisted in the Memory Graph |
| **Current (v2.1.0)** | **1.00** (100%) |
| **Formula** | `episodes_in_graph / total_episodes`; range 0.0–1.0 |
| **Data source** | `src/core/metrics.py`, Memory Graph |
| **Cadence** | Per-episode + aggregated per release |
| **DORA** | N/A |
| **ISO 25010** | Reliability (Maturity), Maintainability (Analysability) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

---

## Derived / Composite Metrics

### 13. TEC (Technical Effort Complexity)

| Field | Value |
|-------|-------|
| **What it measures** | Weighted file-count proxy for codebase effort complexity |
| **Current (v2.1.0)** | CORE: **520.4** · ENT: **1,605.4** · TOTAL: **18,755** |
| **Formula** | `F×files + P×packages + C×configs + R×run_surfaces + T×tests` (coefficients in `tec_ctec_policy.json`) |
| **Data source** | `enterprise/scripts/tec_ctec.py`, `enterprise/governance/tec_ctec_policy.json` |
| **Cadence** | Every release |
| **DORA** | N/A |
| **ISO 25010** | Maintainability (Analysability, Modifiability) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 14. C-TEC (Control-Adjusted TEC)

| Field | Value |
|-------|-------|
| **What it measures** | TEC adjusted for control posture (KPI coverage, risk, change churn) |
| **Current (v2.1.0)** | CORE: **364.3** · ENT: **1,123.8** · TOTAL: **13,128** · ICR: GREEN · PCR: extreme (CCF=0.7) |
| **Formula** | `TEC × KPI_Coverage × RCF × CCF` |
| **Data source** | `enterprise/scripts/tec_ctec.py`, ICR/PCR health reports |
| **Cadence** | Every release |
| **DORA** | N/A |
| **ISO 25010** | Maintainability (Analysability), Security (Integrity) |
| **OTel** | N/A |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

### 15. SSI (System Stability Index)

| Field | Value |
|-------|-------|
| **What it measures** | Nonlinear composite of volatility, drift acceleration, authority, and economics |
| **Current (v2.1.0)** | **59.7**/100 · Gate: **WARN** · Confidence: 0.89 · Drift accel: 0.6825 |
| **Formula** | `(35% × Volatility) + (30% × Drift_Accel) + (20% × Authority) + (15% × Economic)`; 0–100 scale |
| **Data source** | `enterprise/scripts/nonlinear_stability.py`, `enterprise/release_kpis/nonlinear_stability_report.md` |
| **Cadence** | Every release |
| **DORA** | MTTR (partial — SSI incorporates recovery dynamics); Change Failure Rate (partial — drift acceleration) |
| **ISO 25010** | Reliability (Maturity, Availability, Recoverability) |
| **OTel** | Custom gauge: `deepsigma.stability.index` |
| **SMART** | S:PASS · M:PASS · A:PASS · R:PASS · T:PASS · **Net: PASS** |

---

## Summary Matrix (v2.1.0)

| # | KPI | Current | Conf. | DORA | ISO 25010 | OTel | SMART |
|---|-----|--------:|------:|------|-----------|------|-------|
| 1 | Technical Completeness | 10.0/10 | 97% | N/A | Maintainability, Functional Suitability | N/A | PASS |
| 2 | Automation Depth | 10.0/10 | 95% | Deployment Freq (partial) | Maintainability, Perf. Efficiency | N/A | PASS |
| 3 | Authority Modeling | 10.0/10 | 78% | N/A | Security, Reliability | N/A | PASS\* |
| 4 | Enterprise Readiness | 10.0/10 | 97% | N/A | Compatibility, Usability | N/A | PASS |
| 5 | Scalability | 10.0/10 | 92% | N/A | Performance Efficiency | Partial | PASS |
| 6 | Data Integration | 10.0/10 | 95% | N/A | Compatibility, Portability | N/A | PASS |
| 7 | Economic Measurability | 10.0/10 | 85% | N/A | Maintainability, Functional Suitability | N/A | PASS\* |
| 8 | Operational Maturity | 10.0/10 | 95% | CFR + MTTR (partial) | Reliability | N/A | PASS |
| 9 | Coherence Score | 90/100 | — | N/A | Reliability, Functional Suitability | `deepsigma.coherence.score` | PASS |
| 10 | Drift Density | 0.0000 | — | CFR (analogous) | Reliability | `deepsigma.drift.density` | PASS |
| 11 | Authority Coverage | 1.00 | — | N/A | Security | N/A | PASS |
| 12 | Memory Coverage | 1.00 | — | N/A | Reliability, Maintainability | N/A | PASS |
| 13 | TEC | 18,755 | — | N/A | Maintainability | N/A | PASS |
| 14 | C-TEC | 13,128 | — | N/A | Maintainability, Security | N/A | PASS |
| 15 | SSI | 59.7/100 | — | MTTR + CFR (partial) | Reliability | `deepsigma.stability.index` | PASS |

**Release KPI Mean:** 10.0/10 · **Gate:** PASS · **All 8 at production tier**
**Totals:** 15 KPIs · 13 SMART PASS + 2 SMART PASS\* · 0 Experimental · 4 DORA mappings · 4 OTel mappings

---

## DORA Coverage Notes

DeepSigma is an **infrastructure product**, not a deployed web service. DORA's four keys (Deployment Frequency, Lead Time for Changes, Change Failure Rate, MTTR) are oriented toward service delivery. Mappings are therefore partial or analogous:

- **Deployment Frequency** → Automation Depth measures automation breadth, a prerequisite.
- **Lead Time for Changes** → Not directly measured. Could be derived from GitHub PR merge-time data in future.
- **Change Failure Rate** → Drift Density and SSI drift-acceleration components serve as analogues.
- **MTTR** → Scalability benchmark includes wall-clock recovery; SSI incorporates recovery dynamics.

No KPI is force-mapped to DORA where the fit is poor.

## ISO/IEC 25010 Coverage Notes

All eight ISO/IEC 25010 quality characteristics are represented:

| Characteristic | KPIs mapped |
|---------------|-------------|
| Functional Suitability | Technical Completeness, Economic Measurability, Coherence Score |
| Performance Efficiency | Automation Depth, Scalability |
| Compatibility | Enterprise Readiness, Data Integration |
| Usability | Enterprise Readiness |
| Reliability | Authority Modeling, Operational Maturity, Coherence Score, Drift Density, Memory Coverage, SSI |
| Security | Authority Modeling, Authority Coverage, C-TEC |
| Maintainability | Technical Completeness, Automation Depth, Economic Measurability, Memory Coverage, TEC, C-TEC |
| Portability | Data Integration |

## OpenTelemetry Notes

Four KPIs produce values suitable for OTel instrumentation as custom gauges. Metric names follow an internal `deepsigma.<domain>.<metric>` convention (not official OTel semantic conventions). These are candidates for future OTel SDK integration — not yet emitted as traces/metrics/logs.

| Metric name | KPI | Type |
|-------------|-----|------|
| `deepsigma.coherence.score` | Coherence Score | Gauge (0–100) |
| `deepsigma.drift.density` | Drift Density | Gauge (0.0–1.0) |
| `deepsigma.stability.index` | SSI | Gauge (0–100) |
| `deepsigma.benchmark.throughput_rps` | Scalability | Gauge (RPS) |

## SMART Footnotes

**PASS\*** indicates the KPI passes SMART with a qualification on **R (Reproducible)**:

- The score is reproducible *given the same rubric and evidence files*, but involves human judgment in the assessment step.
- If the rubric or evidence artifacts are absent, the KPI must be downgraded to **Experimental** per [kpi_governance.md](./kpi_governance.md).
- KPIs marked PASS\* are: **Authority Modeling** (manual rubric), **Economic Measurability** (TEC cost model assumptions).
