# Prompt OS v2 — Power Automate Integration Mappings

Vendor-neutral automation mappings for connecting Prompt OS workbook tables to organizational data flows. Describes data mapping and triggers — no tenant-specific configuration.

---

## 1. Email / Teams Message → ATOMIC_CLAIMS

**Trigger:** New email or Teams message matching a keyword filter (e.g., subject contains "decision", "claim", "evidence").

### Field Mapping

| Source Field | Target Column | Transform |
|-------------|---------------|-----------|
| (auto-generated) | `ClaimID` | Sequential ID: `CLM-{NNN}` |
| Message body (first sentence or subject) | `Claim` | Extract primary assertion |
| Sender name | `Source` | Full name of sender |
| `"Internal"` if org domain, else `"External"` | `SourceType` | Domain-based classification |
| `50` (default) | `Confidence_pct` | Default; operator adjusts post-capture |
| `50` (default) | `EvidenceStrength_0to100` | Default; operator adjusts post-capture |
| (empty) | `CounterEvidence_0to100` | Populated manually |
| Message received date | `DateCaptured` | ISO 8601 date |
| (empty) | `LinkedDecisionID` | Populated manually |
| Auto-extracted keywords | `Tags` | Top 3 keywords from message body |
| Message URL / thread link | `Notes` | Link back to source message |

### Flow Logic

1. Trigger: new message arrives matching filter
2. Parse message body for primary assertion
3. Classify source type by sender domain
4. Append row to `AtomicClaimsTable` in workbook
5. Send confirmation to operator via Teams notification

---

## 2. Meeting Notes → DECISION_LOG

**Trigger:** New item in designated meeting notes location (e.g., OneNote section, Teams channel, or shared document library) or manual trigger.

### Field Mapping

| Source Field | Target Column | Transform |
|-------------|---------------|-----------|
| (auto-generated) | `DecisionID` | Sequential ID: `DEC-{NNN}` |
| Meeting subject + decision keyword | `Title` | Extract decision statement |
| (default or keyword-derived) | `Category` | Map from meeting category tag |
| Meeting organizer | `Owner` | Full name |
| `"Active"` | `Status` | Default for new entries |
| `50` (default) | `Confidence_pct` | Default; operator adjusts |
| `3` (default) | `BlastRadius_1to5` | Default medium; operator adjusts |
| `3` (default) | `Reversibility_1to5` | Default medium; operator adjusts |
| `"Medium"` | `CostOfDelay` | Default; operator adjusts |
| `"Low"` | `CompressionRisk` | Default; operator adjusts |
| Meeting notes excerpt | `Evidence` | Relevant supporting context |
| (empty) | `CounterEvidence` | Populated manually |
| (empty) | `Assumptions` | Populated manually |
| Meeting date | `DateLogged` | ISO 8601 date |
| Meeting date + 30 days | `ReviewDate` | Default 30-day review cycle |
| (formula) | `PriorityScore` | Auto-computed by workbook |
| Meeting notes URL | `Notes` | Link back to source notes |

### Flow Logic

1. Trigger: new meeting notes posted or manual button press
2. Extract decision statements (keyword: "decided", "agreed", "approved")
3. Create one row per decision identified
4. Append to `DecisionLogTable`
5. Notify owner via email with decision summary and review date

---

## 3. Weekly Scheduled Run → Expiry + Drift Flagging

**Trigger:** Scheduled recurrence (e.g., every Monday at 08:00).

### Actions

#### 3a. Flag Expired Assumptions

| Step | Action | Target |
|------|--------|--------|
| 1 | Read all rows from `AssumptionsTable` | — |
| 2 | Filter where `ExpiryRisk = "RED"` and `Status = "Active"` | — |
| 3 | For each expired assumption: | — |
| 3a | Check if `PatchLogTable` already has an open patch for this `AssumptionID` | `PatchLogTable[TriggerID]` |
| 3b | If no open patch exists, create new `PATCH_LOG` entry | `PatchLogTable` |
| 3c | Set `TriggerType = "Expiry"`, `Severity_GYR = "YELLOW"`, `Status = "Open"` | — |
| 4 | Send summary notification: count of newly flagged assumptions | Operator via Teams/email |

#### 3b. Flag Drift Prompts

| Step | Action | Target |
|------|--------|--------|
| 1 | Read all rows from `PromptLibraryTable` | — |
| 2 | Filter where `DriftFlag = "Major"` and `PromptHealth < 60` | — |
| 3 | For each degraded prompt: | — |
| 3a | Check if `PatchLogTable` already has an open patch for this `PromptID` | `PatchLogTable[TriggerID]` |
| 3b | If no open patch exists, create new `PATCH_LOG` entry | `PatchLogTable` |
| 3c | Set `TriggerType = "Drift"`, `Severity_GYR = "RED"`, `Status = "Open"` | — |
| 4 | Send summary notification: count of degraded prompts | Operator via Teams/email |

#### 3c. Snapshot Dashboard Trends

| Step | Action | Target |
|------|--------|--------|
| 1 | Read current values from `DASHBOARD_V2` KPIs | — |
| 2 | Append new row to `DashboardTrendsTable` | `DashboardTrendsTable` |
| 3 | Set `WeekEnding` = current date | — |
| 4 | Populate all KPI columns from dashboard values | — |

---

## 4. Export Snapshot (Sealed Run)

**Trigger:** Manual button press or post-LLM-session trigger.

### Actions

| Step | Action | Output |
|------|--------|--------|
| 1 | Read all named tables from workbook | In-memory data |
| 2 | Export each table as JSON object | `{ "DecisionLogTable": [...], ... }` |
| 3 | Compute SHA-256 hash of combined JSON | Seal hash |
| 4 | Write seal hash to most recent `LLMOutputTable` row `SealHash` column | Workbook update |
| 5 | Export workbook as PDF (all tabs) | PDF file |
| 6 | Save JSON + PDF to designated archive location | Archive folder |
| 7 | Send confirmation with seal hash and file links | Operator via Teams/email |

### Sealed Run JSON Structure

```json
{
  "seal_version": "2.0",
  "sealed_at": "2026-02-21T14:30:00Z",
  "seal_hash": "sha256:...",
  "tables": {
    "DecisionLogTable": [ ... ],
    "AtomicClaimsTable": [ ... ],
    "AssumptionsTable": [ ... ],
    "PromptLibraryTable": [ ... ],
    "PatchLogTable": [ ... ],
    "LLMOutputTable": [ ... ],
    "DashboardTrendsTable": [ ... ]
  }
}
```

---

## Notes

- All mappings are vendor-neutral. Implement using Power Automate, n8n, Zapier, or equivalent.
- Default values (confidence, blast radius, etc.) should be tuned per organization.
- Notification channels are configurable — Teams, email, Slack, or webhook.
- The sealed export provides an immutable audit trail for governance compliance.
