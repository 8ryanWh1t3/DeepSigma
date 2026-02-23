---
title: "Snowflake Demo — Enterprise Ingress Guide"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-21"
---

# Snowflake Demo — Enterprise Ingress

**What this enables:** Load Prompt OS decision data into Snowflake for enterprise analytics, compliance reporting, and cross-system joins with existing BI pipelines.

---

## Export the Bundle

```bash
python src/tools/prompt_os/export_for_snowflake.py
```

This creates a timestamped folder under `artifacts/snowflake_exports/`:

```
artifacts/snowflake_exports/prompt_os_export_20260221T120000Z/
├── PROMPT_OS_DECISION_LOG.csv
├── PROMPT_OS_ATOMIC_CLAIMS.csv
├── PROMPT_OS_ASSUMPTIONS.csv
├── PROMPT_OS_PATCH_LOG.csv
├── PROMPT_OS_PROMPT_LIBRARY.csv
├── PROMPT_OS_LLM_OUTPUT.csv
├── PROMPT_OS_DASHBOARD_TRENDS.csv
├── SEALED_RUNS/
│   └── RUN-001_20260221T120000Z.json
│   └── ...
└── MANIFEST.json
```

---

## Table Name Mapping

| Source CSV | Snowflake Table |
|------------|-----------------|
| `decision_log.csv` | `PROMPT_OS_DECISION_LOG` |
| `atomic_claims.csv` | `PROMPT_OS_ATOMIC_CLAIMS` |
| `assumptions.csv` | `PROMPT_OS_ASSUMPTIONS` |
| `patch_log.csv` | `PROMPT_OS_PATCH_LOG` |
| `prompt_library.csv` | `PROMPT_OS_PROMPT_LIBRARY` |
| `llm_output.csv` | `PROMPT_OS_LLM_OUTPUT` |
| `dashboard_trends.csv` | `PROMPT_OS_DASHBOARD_TRENDS` |

---

## Staging & COPY INTO

### 1. Create a stage

```sql
CREATE OR REPLACE STAGE prompt_os_stage
  FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"');
```

### 2. Upload files

```bash
PUT file://artifacts/snowflake_exports/prompt_os_export_*/PROMPT_OS_*.csv @prompt_os_stage;
```

### 3. Create tables and load

```sql
-- Decision Log
CREATE TABLE IF NOT EXISTS PROMPT_OS_DECISION_LOG (
  DecisionID        VARCHAR,
  Title             VARCHAR,
  Category          VARCHAR,
  Owner             VARCHAR,
  Status            VARCHAR,
  Confidence_pct    NUMBER,
  BlastRadius_1to5  NUMBER,
  Reversibility_1to5 NUMBER,
  CostOfDelay       VARCHAR,
  CompressionRisk   VARCHAR,
  Evidence          VARCHAR,
  CounterEvidence   VARCHAR,
  Assumptions       VARCHAR,
  DateLogged        DATE,
  ReviewDate        DATE,
  PriorityScore     FLOAT,
  Notes             VARCHAR
);

COPY INTO PROMPT_OS_DECISION_LOG
  FROM @prompt_os_stage/PROMPT_OS_DECISION_LOG.csv
  FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"');

-- Repeat for each table (ATOMIC_CLAIMS, ASSUMPTIONS, PATCH_LOG, etc.)
```

---

## Sealed Runs as VARIANT

Sealed run JSONs can be loaded as Snowflake VARIANT for flexible querying:

```sql
CREATE TABLE IF NOT EXISTS PROMPT_OS_SEALED_RUNS (
  filename  VARCHAR,
  run_data  VARIANT,
  loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Stage and load
PUT file://artifacts/snowflake_exports/prompt_os_export_*/SEALED_RUNS/*.json @prompt_os_stage/sealed/;

COPY INTO PROMPT_OS_SEALED_RUNS (filename, run_data)
  FROM (
    SELECT
      METADATA$FILENAME,
      PARSE_JSON($1)
    FROM @prompt_os_stage/sealed/
  )
  FILE_FORMAT = (TYPE = 'JSON');
```

---

## Example Queries

### Count RED patches

```sql
SELECT COUNT(*) AS red_patch_count
FROM PROMPT_OS_PATCH_LOG
WHERE Severity_GYR = 'RED' AND Status = 'Open';
```

### Average confidence across active decisions

```sql
SELECT AVG(Confidence_pct) AS avg_confidence
FROM PROMPT_OS_DECISION_LOG
WHERE Status = 'Active';
```

### Newest sealed run

```sql
SELECT
  run_data:meta.run_id::VARCHAR     AS run_id,
  run_data:meta.session_date::DATE  AS session_date,
  run_data:meta.operator::VARCHAR   AS operator,
  run_data:drift.severity::VARCHAR  AS drift_severity
FROM PROMPT_OS_SEALED_RUNS
ORDER BY loaded_at DESC
LIMIT 1;
```

### Assumptions expiring within 30 days

```sql
SELECT AssumptionID, Assumption, ExpiryDate, ExpiryRisk
FROM PROMPT_OS_ASSUMPTIONS
WHERE ExpiryDate <= DATEADD('day', 30, CURRENT_DATE())
  AND Status = 'Active'
ORDER BY ExpiryDate;
```

---

## Related

- [SEALED_RUN_EXPORT_SPEC.md](SEALED_RUN_EXPORT_SPEC.md) — Sealed run JSON format
- [TABS_AND_SCHEMA.md](TABS_AND_SCHEMA.md) — Full column-level schema
- [DATA_VALIDATION_MAP.md](DATA_VALIDATION_MAP.md) — Enum values for all tables
