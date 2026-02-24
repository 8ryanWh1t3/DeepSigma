# Prompt OS v2 — Prompt Health Telemetry

Track prompt usage, detect output drift, and auto-update PromptLibraryTable.

---

## Overview

The telemetry system provides three capabilities:

1. **Usage tracking** — Record each prompt use with success/failure and quality rating
2. **Drift detection** — Compare LLM output structure against expected format
3. **Workbook sync** — Update PromptLibraryTable (UsageCount, SuccessRate, DriftFlag) from telemetry data

---

## Quick Start

```bash
# Record a successful prompt use
python -m tools.prompt_health_telemetry record --prompt-id PRM-001 --success --rating 4.5

# Check an LLM output for drift
python -m tools.prompt_health_telemetry check-drift --prompt-id PRM-001 --output-file output.txt

# Analyze all telemetry data
python -m tools.prompt_health_telemetry analyze

# Update the workbook from telemetry
python -m tools.prompt_health_telemetry update-workbook

# Full report
python -m tools.prompt_health_telemetry report
```

---

## Telemetry Data

Telemetry is stored in `data/prompt_telemetry/`:

| File | Contents |
|------|----------|
| `usage_log.csv` | Every prompt usage event (timestamp, prompt_id, success, rating, model) |
| `drift_log.csv` | Detected drift events (timestamp, prompt_id, drift_type, severity, detail) |

---

## Drift Detection

The system checks LLM output against expected sections for each prompt:

| Prompt | Expected Sections |
|--------|-------------------|
| PRM-001 (Executive Analysis) | Executive Summary, Recommended Action, Facts, Assumptions, Failure Modes, Next actions |
| PRM-002 (Reality Assessment) | Observable facts, Story, Assumptions, Contradicting evidence, Drift Check, Grounded decision |
| PRM-003 (Team Workbook Triage) | TOP RISKS, TOP ACTIONS, SYSTEM OBSERVATIONS, Seal |
| PRM-004 (Assumption Audit) | Assumptions, Expiry, Confidence |

### Drift Severity Thresholds

| Coverage | Severity | Action |
|----------|----------|--------|
| ≥ 90% | None | Continue use |
| 70–89% | Minor | Schedule review |
| < 70% | Major | Immediate rewrite |

---

## PromptLibraryTable Integration

The `update-workbook` command syncs telemetry data to the workbook:

| Telemetry Field | Target Column | Logic |
|-----------------|---------------|-------|
| Total uses | UsageCount | Incremented by telemetry count |
| Success rate | SuccessRate_pct | Computed from success/total |
| Average rating | AvgRating_1to5 | Mean of all ratings |
| Drift events | DriftFlag | ≥3 events = Major, ≥1 = Minor, 0 = None |
| Last use date | LastUsed | Set to today |

PromptHealth is auto-computed by the workbook formula after DriftFlag and SuccessRate are updated.

---

## CI Integration

Add to your CI pipeline:

```bash
# Validate that no prompts have Major drift
python -m tools.prompt_health_telemetry analyze | grep -q "Major" && exit 1 || exit 0
```
