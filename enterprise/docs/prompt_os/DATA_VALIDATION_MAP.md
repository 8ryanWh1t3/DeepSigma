# Data Validation Map

Enum columns and their allowed values for every named table in Coherence Prompt OS v2.

All values below are the **single source of truth**, matching `schemas/prompt_os/prompt_os_schema_v2.json` exactly. Excel data validation dropdowns should enforce these lists.

---

## DecisionLogTable

| Column | Allowed Values |
|--------|---------------|
| `Category` | Technology \| Operations \| Finance \| Strategy \| People |
| `Status` | Active \| Deferred \| Closed \| Superseded |
| `CostOfDelay` | Low \| Medium \| High |
| `CompressionRisk` | Low \| Medium \| High |

**Numeric ranges:**

| Column | Type | Min | Max |
|--------|------|-----|-----|
| `Confidence_pct` | integer | 0 | 100 |
| `BlastRadius_1to5` | integer | 1 | 5 |
| `Reversibility_1to5` | integer | 1 | 5 |

---

## AtomicClaimsTable

| Column | Allowed Values |
|--------|---------------|
| `SourceType` | Internal \| External \| LLM \| Expert |

**Numeric ranges:**

| Column | Type | Min | Max |
|--------|------|-----|-----|
| `Confidence_pct` | integer | 0 | 100 |
| `EvidenceStrength_0to100` | integer | 0 | 100 |
| `CounterEvidence_0to100` | integer | 0 | 100 |
| `StaleDays` | integer | 0 | — |
| `CredibilityScore` | number | 0 | 100 |

---

## AssumptionsTable

| Column | Allowed Values |
|--------|---------------|
| `ExpiryRisk` | RED \| YELLOW \| GREEN |
| `Status` | Active \| Expired \| Validated \| Invalidated |

**Numeric ranges:**

| Column | Type | Min | Max |
|--------|------|-----|-----|
| `Confidence_pct` | integer | 0 | 100 |
| `HalfLife_days` | integer | 1 | — |

---

## PatchLogTable

| Column | Allowed Values |
|--------|---------------|
| `TriggerType` | Drift \| Expiry \| Manual \| LLM |
| `Severity_GYR` | GREEN \| YELLOW \| RED |
| `Status` | Open \| In Progress \| Resolved \| Wont Fix |

---

## PromptLibraryTable

| Column | Allowed Values |
|--------|---------------|
| `Category` | Decision \| Perception \| Governance \| Maintenance \| Analysis |
| `DriftFlag` | None \| Minor \| Major |

**Numeric ranges:**

| Column | Type | Min | Max |
|--------|------|-----|-----|
| `SuccessRate_pct` | integer | 0 | 100 |
| `AvgRating_1to5` | number | 1 | 5 |
| `UsageCount` | integer | 0 | — |
| `PromptHealth` | number | 0 | 100 |

---

## LLMOutputTable

No enum columns. Validation is structural (required fields, date formats).

**Numeric ranges:**

| Column | Type | Min | Max |
|--------|------|-----|-----|
| `SummaryConfidence_pct` | integer | 0 | 100 |

---

## DashboardTrendsTable

No enum columns. All fields are date or integer.

**Numeric ranges:**

| Column | Type | Min | Max |
|--------|------|-----|-----|
| `ActiveDecisions` | integer | 0 | — |
| `AvgConfidence` | integer | 0 | 100 |
| `LowCredClaims` | integer | 0 | — |
| `ExpiredAssumptions` | integer | 0 | — |
| `OpenPatches` | integer | 0 | — |
| `REDPatches` | integer | 0 | — |
| `AvgPromptHealth` | integer | 0 | 100 |

---

## Applying in Excel

To add data validation dropdowns in the workbook:

1. Select the target column cells (e.g., `DECISION_LOG!E2:E1000` for Status)
2. **Data** → **Validation** → **Allow: List**
3. Enter the comma-separated values from the table above
4. Set **Error Alert** → **Style: Stop** to prevent invalid entries

The workbook at `artifacts/excel/Coherence_Prompt_OS_v2.xlsx` includes data validation dropdowns for all enum columns listed above.

---

## Related Docs

- [TABS_AND_SCHEMA.md](TABS_AND_SCHEMA.md) — Full column-level schema
- [SCORING.md](SCORING.md) — Computed field formulas
- Schema: `schemas/prompt_os/prompt_os_schema_v2.json`
