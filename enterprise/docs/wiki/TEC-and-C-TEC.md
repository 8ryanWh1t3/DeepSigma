# TEC and C-TEC

## Overview

DeepSigma produces deterministic economic metrics from repo telemetry. Two pipelines run independently and serve different purposes:

| Pipeline | Script | What it measures | Output |
| --- | --- | --- | --- |
| **TEC / C-TEC v2** | `enterprise/scripts/tec_ctec.py` | Surface inventory complexity, governance control coverage | `release_kpis/health/tec_ctec_latest.json` |
| **TEC Estimate** | `enterprise/scripts/tec_estimate.py` | Effort hours from issues, PRs, and repo structure | `release_kpis/tec_internal.json`, `tec_executive.json`, `tec_dod.json` |

Both pipelines produce tiered cost estimates (Internal, Executive, CustomerOrg) with uncertainty bands.

---

## TEC (Technical Effort Complexity)

TEC scores a codebase edition by counting shipped surfaces and weighting them by governance significance.

### Formula

```
TEC = F*files + P*packages + C*configs + R*run_surfaces + T*tests
```

### Coefficients

| Symbol | Weight | What it counts |
| --- | --- | --- |
| F | 1.0 | All files in edition scope |
| P | 3.0 | Python packages (`__init__.py` directories) |
| C | 0.2 | Config files (`.yaml`, `.json`, `.toml`, `.ini`, `.cfg`) |
| R | 2.0 | Run surfaces (`run_*.py`, `demo_*.sh`, `if __name__ == "__main__"`) |
| T | 2.0 | Test files (`test_*.py`, `*_test.py`) |

Coefficients are configurable in `enterprise/governance/tec_ctec_policy.json` under `tec_formula`.

### Edition Scoping

TEC is computed three times against different directory trees:

| Edition | Directories |
| --- | --- |
| **core** | `src/core`, `src/coherence_ops`, `docs/examples/demo-stack`, `tests` |
| **enterprise** | `enterprise/src`, `enterprise/dashboard`, `enterprise/docs`, `enterprise/scripts`, `enterprise/release_kpis`, `tests-enterprise` |
| **total** | `.` (entire repo) |

Edition roots are configurable in `tec_ctec_policy.json` under `edition_roots`.

---

## C-TEC (Control-Adjusted TEC)

C-TEC discounts TEC by governance health. A high TEC with poor control coverage produces a lower C-TEC, reflecting that uncontrolled complexity is a liability, not an asset.

### Formula

```
C-TEC = TEC * KPI_Coverage * RCF * CCF
```

Where:

- **KPI_Coverage** = fraction of control checks passing (0.0 to 1.0)
- **RCF** = Risk Control Factor from issue health (ICR)
- **CCF** = Change Control Factor from PR churn (PCR)

### KPI Coverage Checks

Control coverage is evaluated separately for each edition:

**Core checks:**

| Check | Passes when |
| --- | --- |
| `money_demo` | `run_money_demo.sh` exists |
| `baseline` | `core_baseline.py` exists and `CORE_BASELINE_REPORT.md` generated |
| `core_tests` | `tests/` directory exists |
| `boundary_guard` | `enterprise/scripts/edition_guard.py` exists |
| `secret_scan` | `enterprise/scripts/secret_scan.py` exists |
| `docs_path_to_run` | `README.md` references `run_money_demo.sh` |

**Enterprise checks:**

| Check | Passes when |
| --- | --- |
| `enterprise_demo` | `run_enterprise_demo.sh` exists |
| `enterprise_tests` | `tests-enterprise/` directory exists |
| `deploy_sanity` | `enterprise/docker/` and `enterprise/charts/` exist |
| `connector_smokes` | Mesh WAN or pilot-in-a-box script exists |
| `boundary_guard` | `enterprise/scripts/edition_guard.py` exists |
| `secret_scan` | `enterprise/scripts/secret_scan.py` exists |

Total KPI coverage is the average of core and enterprise coverage.

### RCF (Risk Control Factor)

Derived from the Issue Control Rating (ICR). The ICR tracks open issue risk; its status maps to a multiplier:

| ICR Status | RCF | Meaning |
| --- | --- | --- |
| GREEN | 1.0 | Issue risk is managed |
| YELLOW | 0.85 | Moderate open issue risk |
| RED | 0.6 | High open issue risk |

Source: `release_kpis/health/icr_latest.json`

### CCF (Change Control Factor)

Derived from the PR Change Rating (PCR). The PCR measures 14-day PR churn volume; its load bucket maps to a multiplier:

| Load Bucket | CCF | CL14 Threshold |
| --- | --- | --- |
| low | 1.0 | <= 25 |
| medium | 0.9 | <= 60 |
| high | 0.8 | <= 120 |
| extreme | 0.7 | > 120 |

CL14 = total `additions + deletions` across PRs merged in the last 14 days.

Source: `release_kpis/health/pcr_latest.json`

### R-TEC (Risk-Adjusted TEC)

Adds open issue risk directly to TEC:

```
R-TEC = TEC + (2 * RL_open)
```

Where `RL_open` is the count of open risk-labeled issues from the ICR.

---

## Effort Estimation (TEC Estimate)

The effort estimation pipeline converts issue and PR telemetry into hours.

### Base Hours

Each component contributes hours independently:

| Component | Source | Hours |
| --- | --- | --- |
| Issue hours | `type:feature` = 8, `type:bug` = 3, `type:debt` = 5, `type:doc` = 1.5 | Per issue, multiplied by severity |
| Severity multiplier | `sev:P0` = 2.0x, `sev:P1` = 1.5x, `sev:P2` = 1.0x, `sev:P3` = 0.6x | Applied to issue base |
| Security floor | 12 hours minimum for any issue with `security` or `sec:*` labels | Overrides type base if higher |
| PR overhead | 1.5 hours per merged PR | Flat |
| Workflow hours | 5 hours per `.github/workflows/*.yml` file | Flat |
| Test file hours | 2 hours per `test_*.py` file | Flat |
| Doc file hours | 1.5 hours per `docs/**/*.md` file | Flat |
| Committee cycles | 8 hours per issue with `committee:*`, `design-review`, `security-review`, or `needs-approval` labels | Flat |

```
Base_Hours = Issue_Hours + PR_Overhead + Workflow_Hours + Test_Hours + Doc_Hours + Committee_Hours
```

### Complexity Index

Each issue gets a complexity index that multiplies its base hours. The index is the product of four multipliers:

```
Complexity_Index = PR_Mult * Subsystem_Mult * Duration_Mult * Dependency_Mult
```

**PR Complexity Multiplier**

Measures code churn from PRs linked to the issue:

```
pr_score = min(loc_delta / 500, 3.0) + min(changed_files / 10, 2.0)
PR_Mult = 1.0 + min(pr_score * 0.15, 1.0)
```

Range: 1.0 to 2.0

**Subsystem Multiplier**

Counts cross-subsystem touch points (`security`, `authority`, `kpi`, `ci`):

```
Subsystem_Mult = 1.0 + min((subsystem_count - 1) * 0.15, 0.6)
```

Range: 1.0 to 1.6

**Duration Multiplier**

Issues open longer than 14 days get a duration penalty:

```
duration_over = max(duration_days - 14, 0)
Duration_Mult = 1.0 + min(duration_over / 30, 0.5)
```

Range: 1.0 to 1.5

**Dependency Multiplier**

Counts `#issue` cross-references in the issue body:

```
Dependency_Mult = 1.0 + min(dependency_refs * 0.05, 0.4)
```

Range: 1.0 to 1.4

**Aggregate complexity hours:**

```
Complexity_Hours = sum(issue_base_hours[i] * complexity_index[i])
C-TEC_Hours = Complexity_Hours + PR_Overhead + Workflow_Hours + Test_Hours + Doc_Hours + Committee_Hours
```

### Insights Adjustment

If `release_kpis/insights_metrics.json` exists and insights are enabled, C-TEC hours are adjusted:

- **Score component**: Higher insight scores (above neutral 5.0) reduce effort up to 12%. Lower scores increase effort up to 18%.
- **Signal component**: Each active signal adds 1.5% complexity, capped at 12%.

```
factor = 1.0 + score_component + signal_component
Adjusted_Hours = C-TEC_Hours * factor
```

Factor range: 0.88 to 1.30

---

## Uncertainty Bands

Both pipelines apply uncertainty bands to final hours before costing:

| Band | Multiplier |
| --- | --- |
| Low | 0.80x |
| Base | 1.00x |
| High | 1.35x |

---

## Tiered Billing

Three billing tiers produce cost estimates from the same hour base:

| Tier | Rate | Use Case |
| --- | --- | --- |
| Internal | $150/hr | Internal planning and resource allocation |
| Executive | $225/hr | Executive briefings and budget requests |
| CustomerOrg Fully Burdened | $275/hr | Government contract pricing (DCAA-compatible) |

Each tier gets all three uncertainty bands, producing a 3x3 matrix of hours and costs.

---

## Output Artifacts

### From `tec_ctec.py` (Surface Inventory)

| File | Content |
| --- | --- |
| `release_kpis/health/tec_ctec_latest.json` | Full payload: inventory, TEC, C-TEC, R-TEC, factors, controls |
| `release_kpis/health/tec_ctec_latest.md` | Human-readable summary |
| `release_kpis/health/xray_health_block.md` | One-line-per-edition health block |
| `release_kpis/TEC_SUMMARY.md` | Factors, edition metrics, tiered cost estimates |
| `release_kpis/tec_internal.json` | Internal tier with cost bands |
| `release_kpis/tec_executive.json` | Executive tier with cost bands |
| `release_kpis/tec_dod.json` | CustomerOrg tier with cost bands |
| `release_kpis/health/history/TEC_SNAPSHOT_YYYY-MM-DD.json` | Daily snapshot (with `--snapshot` flag) |

### From `tec_estimate.py` (Effort Estimation)

| File | Content |
| --- | --- |
| `release_kpis/tec_internal.json` | Internal tier: counts, hours breakdown, complexity, tiers |
| `release_kpis/tec_executive.json` | Executive tier |
| `release_kpis/tec_dod.json` | CustomerOrg tier |
| `release_kpis/TEC_SUMMARY.md` | Counts, effort breakdown, complexity stats, insights, tiers |

Note: Both pipelines write to the same output paths. The effort estimation pipeline runs second in CI and overwrites the surface inventory outputs, adding the issue/PR-derived effort model.

---

## Configuration Files

| File | Format | What it configures |
| --- | --- | --- |
| `enterprise/governance/tec_ctec_policy.json` | JSON | TEC formula coefficients, RCF/CCF maps, billing rates, uncertainty bands, edition roots |
| `enterprise/governance/tec_weights.yaml` | YAML | Issue hour weights, severity multipliers, complexity tuning, insights adjustment |

---

## CLI Usage

### Surface inventory + C-TEC

```bash
python enterprise/scripts/tec_ctec.py
python enterprise/scripts/tec_ctec.py --snapshot   # also writes daily history
```

### Effort estimation

```bash
python enterprise/scripts/tec_estimate.py
```

Requires `release_kpis/issues_all.json` and `release_kpis/prs_merged.json` (generated by KPI pipeline).

---

## See Also

- [SLOs and Metrics](SLOs-and-Metrics) — SLO targets and Repo Radar KPI
- [C-TEC Pipeline diagram](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/12-c-tec-pipeline.md) — Visual flowchart
- [KPI Confidence Bands Flow](https://github.com/8ryanWh1t3/DeepSigma/blob/main/enterprise/docs/mermaid/14-kpi-confidence-bands-flow.md) — Evidence scoring pipeline
