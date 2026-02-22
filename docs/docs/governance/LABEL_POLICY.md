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

## Rules
1) Every issue that should move the Repo Radar MUST have exactly:
   - 1 KPI label
   - 1 Severity label
   - 1 Type label
2) No alternate spellings. No duplicates. No synonyms.
3) If an issue has sev:P0 and is open, KPI is capped (per kpi_issue_map.yaml).
