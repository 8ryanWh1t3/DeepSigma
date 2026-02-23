# Label Policy (Canonical)

## KPI labels (exact)
- kpi:technical_completeness
- kpi:automation_depth
- kpi:authority_modeling
- kpi:enterprise_readiness
- kpi:scalability
- kpi:data_integration
- kpi:economic_measurability
- kpi:operational_maturity

## Severity labels (exact)
- sev:P0
- sev:P1
- sev:P2
- sev:P3

## Type labels (exact)
- type:feature
- type:bug
- type:debt
- type:doc

## Lane labels (v2.1.0 intake)
- lane:epic
- lane:provider-layer
- lane:authority
- lane:telemetry
- lane:policy
- lane:recovery-scale
- lane:benchmarks
- lane:automation-gate
- lane:audit-pack

## Rules
1) Every issue that should move the Repo Radar MUST have exactly:
   - 1 KPI label
   - 1 Severity label
   - 1 Type label
2) No alternate spellings. No duplicates. No synonyms.
3) If an issue has sev:P0 and is open, KPI is capped (per kpi_issue_map.yaml).
4) Every `v2.1.0 (DISR Architecture)` issue MUST have exactly one `lane:*` label.
