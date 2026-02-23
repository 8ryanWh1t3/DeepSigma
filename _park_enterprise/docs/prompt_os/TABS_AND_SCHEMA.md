# Prompt OS v2 — Tabs and Schema Reference

Full column-level schema for each tab in `Coherence_Prompt_OS_v2.xlsx`.

---

## DECISION_LOG

**Table Name:** `DecisionLogTable`
**Purpose:** Record structured decisions with evidence, scoring, and review dates.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| DecisionID | string | Yes | Unique identifier (e.g., `DEC-001`) |
| Title | string | Yes | Short decision title |
| Category | enum | Yes | `Technology` · `Operations` · `Finance` · `Strategy` · `People` |
| Owner | string | Yes | Decision owner name |
| Status | enum | Yes | `Active` · `Deferred` · `Closed` · `Superseded` |
| Confidence_pct | int (0–100) | Yes | Decision confidence percentage |
| BlastRadius_1to5 | int (1–5) | Yes | Impact scope: 1 = isolated, 5 = organization-wide |
| Reversibility_1to5 | int (1–5) | Yes | Ease of reversal: 1 = irreversible, 5 = trivially reversible |
| CostOfDelay | enum | Yes | `Low` · `Medium` · `High` |
| CompressionRisk | enum | Yes | `Low` · `Medium` · `High` |
| Evidence | string | Yes | Supporting evidence summary |
| CounterEvidence | string | No | Contradicting evidence summary |
| Assumptions | string | No | Key assumptions (free text) |
| DateLogged | date | Yes | Date decision was recorded |
| ReviewDate | date | Yes | Scheduled review date |
| PriorityScore | float (formula) | Auto | Computed priority score |
| Notes | string | No | Additional context |

---

## ATOMIC_CLAIMS

**Table Name:** `AtomicClaimsTable`
**Purpose:** Track individual truth claims with source attribution and credibility scoring.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| ClaimID | string | Yes | Unique identifier (e.g., `CLM-001`) |
| Claim | string | Yes | The atomic claim statement |
| Source | string | Yes | Where the claim originated |
| SourceType | enum | Yes | `Internal` · `External` · `LLM` · `Expert` |
| Confidence_pct | int (0–100) | Yes | Confidence in claim accuracy |
| EvidenceStrength_0to100 | int (0–100) | Yes | Strength of supporting evidence |
| CounterEvidence_0to100 | int (0–100) | No | Strength of contradicting evidence |
| DateCaptured | date | Yes | Date claim was recorded |
| StaleDays | int (formula) | Auto | Days since capture (`=TODAY()-DateCaptured`) |
| CredibilityScore | float (formula) | Auto | Computed credibility (0–100) |
| LinkedDecisionID | string | No | Reference to DecisionLogTable |
| Tags | string | No | Comma-separated tags |
| Notes | string | No | Additional context |

---

## PROMPT_LIBRARY

**Table Name:** `PromptLibraryTable`
**Purpose:** Manage prompt assets with version tracking, usage metrics, and health scoring.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| PromptID | string | Yes | Unique identifier (e.g., `PRM-001`) |
| PromptName | string | Yes | Human-readable prompt name |
| Category | enum | Yes | `Decision` · `Perception` · `Governance` · `Maintenance` · `Analysis` |
| Version | string | Yes | Semantic version (e.g., `1.2`) |
| SuccessRate_pct | int (0–100) | Yes | Percentage of successful uses |
| AvgRating_1to5 | float (1–5) | Yes | Average quality rating |
| DriftFlag | enum | Yes | `None` · `Minor` · `Major` |
| UsageCount | int | No | Total times used |
| LastUsed | date | No | Date of most recent use |
| PromptHealth | float (formula) | Auto | Computed health score (0–100) |
| Owner | string | No | Prompt owner |
| Notes | string | No | Additional context |

---

## ASSUMPTIONS

**Table Name:** `AssumptionsTable`
**Purpose:** Track assumptions with half-life decay and expiry risk coloring.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| AssumptionID | string | Yes | Unique identifier (e.g., `ASM-001`) |
| Assumption | string | Yes | The assumption statement |
| LinkedDecisionID | string | Yes | Reference to DecisionLogTable |
| Confidence_pct | int (0–100) | Yes | Confidence in assumption validity |
| CreatedDate | date | Yes | Date assumption was recorded |
| HalfLife_days | int | Yes | Expected validity period in days |
| ExpiryDate | date (formula) | Auto | `=CreatedDate + HalfLife_days` |
| ExpiryRisk | enum (formula) | Auto | `RED` · `YELLOW` · `GREEN` |
| DisconfirmSignal | string | Yes | What would invalidate this assumption |
| LastReviewed | date | No | Date of most recent review |
| Status | enum | Yes | `Active` · `Expired` · `Validated` · `Invalidated` |
| Notes | string | No | Additional context |

### ExpiryRisk Logic

| Condition | Value |
|-----------|-------|
| ExpiryDate < TODAY() | `RED` |
| ExpiryDate < TODAY() + 14 days | `YELLOW` |
| ExpiryDate >= TODAY() + 14 days | `GREEN` |

---

## PATCH_LOG

**Table Name:** `PatchLogTable`
**Purpose:** Log drift events and corrective patches triggered by assumption expiry or claim drift.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| PatchID | string | Yes | Unique identifier (e.g., `PAT-001`) |
| TriggerType | enum | Yes | `Drift` · `Expiry` · `Manual` · `LLM` |
| TriggerID | string | Yes | ID of the triggering record (e.g., `ASM-002`) |
| Description | string | Yes | What the patch addresses |
| Severity_GYR | enum | Yes | `GREEN` · `YELLOW` · `RED` |
| Status | enum | Yes | `Open` · `In Progress` · `Resolved` · `Wont Fix` |
| Owner | string | Yes | Patch owner |
| DateCreated | date | Yes | Date patch was opened |
| DateResolved | date | No | Date patch was resolved |
| Resolution | string | No | How the patch was resolved |
| Notes | string | No | Additional context |

---

## LLM_OUTPUT

**Table Name:** `LLMOutputTable`
**Purpose:** Capture structured LLM session outputs for audit trail and sealed runs.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| RunID | string | Yes | Unique run identifier (e.g., `RUN-001`) |
| SessionDate | date | Yes | Date of LLM session |
| Model | string | Yes | Model used (e.g., `claude-opus-4`) |
| TopActions | string | Yes | Top 3 recommended actions |
| TopRisks | string | Yes | Top 3 identified risks |
| SuggestedUpdates | string | No | Recommended workbook updates |
| SealHash | string | No | SHA-256 hash for sealed run verification |
| SummaryConfidence_pct | int (0–100) | Yes | LLM's self-assessed confidence |
| NextReviewDate | date | Yes | Suggested next review date |
| Operator | string | Yes | Person who ran the session |
| Notes | string | No | Additional context |

---

## DASHBOARD_V2

**Purpose:** Live KPI summary pulling from all named tables. Not a named table — read-only summary view.

| KPI | Formula Source |
|-----|---------------|
| Total Active Decisions | `COUNTIF(DecisionLogTable[Status],"Active")` |
| Avg Decision Confidence | `AVERAGE(DecisionLogTable[Confidence_pct])` |
| Claims Below Credibility 60 | `COUNTIF(AtomicClaimsTable[CredibilityScore],"<60")` |
| Expired Assumptions (RED) | `COUNTIF(AssumptionsTable[ExpiryRisk],"RED")` |
| Open Patches | `COUNTIF(PatchLogTable[Status],"Open")` |
| RED Severity Patches | `COUNTIF(PatchLogTable[Severity_GYR],"RED")` |
| Avg Prompt Health | `AVERAGE(PromptLibraryTable[PromptHealth])` |
| Prompts with Major Drift | `COUNTIF(PromptLibraryTable[DriftFlag],"Major")` |
| Total LLM Runs | `COUNTA(LLMOutputTable[RunID])` |

---

## DASHBOARD_TRENDS

**Table Name:** `DashboardTrendsTable`
**Purpose:** Weekly snapshot history for trend analysis and reporting.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| WeekEnding | date | Yes | End date of the snapshot week |
| ActiveDecisions | int | Yes | Count of active decisions |
| AvgConfidence | int | Yes | Average confidence across active decisions |
| LowCredClaims | int | Yes | Count of claims with CredibilityScore < 60 |
| ExpiredAssumptions | int | Yes | Count of RED expiry risk assumptions |
| OpenPatches | int | Yes | Count of open patches |
| REDPatches | int | Yes | Count of RED severity patches |
| AvgPromptHealth | int | Yes | Average prompt health score |
| Notes | string | No | Week summary notes |

---

## Enum Reference

| Enum | Values |
|------|--------|
| Decision Status | `Active` · `Deferred` · `Closed` · `Superseded` |
| Decision Category | `Technology` · `Operations` · `Finance` · `Strategy` · `People` |
| CostOfDelay | `Low` · `Medium` · `High` |
| CompressionRisk | `Low` · `Medium` · `High` |
| SourceType | `Internal` · `External` · `LLM` · `Expert` |
| DriftFlag | `None` · `Minor` · `Major` |
| Severity_GYR | `GREEN` · `YELLOW` · `RED` |
| ExpiryRisk | `RED` · `YELLOW` · `GREEN` |
| Assumption Status | `Active` · `Expired` · `Validated` · `Invalidated` |
| Patch Status | `Open` · `In Progress` · `Resolved` · `Wont Fix` |
| Patch TriggerType | `Drift` · `Expiry` · `Manual` · `LLM` |
| Prompt Category | `Decision` · `Perception` · `Governance` · `Maintenance` · `Analysis` |
