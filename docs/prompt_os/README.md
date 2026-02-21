# Coherence Prompt OS v2

**Excel-first cognition container for structured institutional decision-making.**

---

## What Is Prompt OS?

Prompt OS is a workbook-based decision infrastructure that implements three cognitive loops:

1. **Perception** — Reality checks strip narrative from observation (`REALITY_ENGINE`)
2. **Decision** — Structured analysis with scored options and failure modes (`EXECUTIVE_ENGINE` → `DECISION_LOG`)
3. **Memory** — Claims, assumptions, and patches keep institutional knowledge alive and self-correcting (`ATOMIC_CLAIMS` → `ASSUMPTIONS` → `PATCH_LOG`)

The system is designed to run inside a shared Excel workbook. No code required. LLM sessions read the workbook as context and output structured actions.

---

## Workbook Tabs Overview

| Tab | Purpose |
|-----|---------|
| `DECISION_LOG` | Record decisions with evidence, confidence, blast radius, and priority scoring |
| `ATOMIC_CLAIMS` | Track individual truth claims with source, confidence, and credibility scoring |
| `PROMPT_LIBRARY` | Manage prompt assets with health scoring and drift detection |
| `ASSUMPTIONS` | Track assumptions with half-life, expiry dates, and risk coloring |
| `PATCH_LOG` | Log drift events and corrective patches with severity |
| `LLM_OUTPUT` | Capture LLM session outputs — top actions, risks, seal hashes |
| `DASHBOARD_V2` | Live KPI summary pulling from all tables |
| `DASHBOARD_TRENDS` | Weekly snapshot history for trend analysis |
| `REALITY_ENGINE` | Structured perception checks — separate fact from narrative |
| `EXECUTIVE_ENGINE` | Full structured decision analysis with options comparison |

---

## Named Tables

Each core tab exposes a named Excel table for formula cross-references and Power Automate integration:

| Table Name | Tab |
|------------|-----|
| `DecisionLogTable` | DECISION_LOG |
| `AtomicClaimsTable` | ATOMIC_CLAIMS |
| `PromptLibraryTable` | PROMPT_LIBRARY |
| `AssumptionsTable` | ASSUMPTIONS |
| `PatchLogTable` | PATCH_LOG |
| `LLMOutputTable` | LLM_OUTPUT |
| `DashboardTrendsTable` | DASHBOARD_TRENDS |

---

## Scoring Overview

The workbook implements four scoring systems:

| Score | Range | Purpose |
|-------|-------|---------|
| **PriorityScore** | 0–~8 | Ranks decisions by blast radius, reversibility, confidence, cost-of-delay, compression risk |
| **CredibilityScore** | 0–100 | Scores truth claims by evidence strength, counter-evidence, and staleness |
| **PromptHealth** | 0–100 | Scores prompt assets by success rate, rating, and drift |
| **ExpiryRisk** | RED / YELLOW / GREEN | Flags assumptions approaching or past their half-life expiry |

See [SCORING.md](SCORING.md) for full formula documentation.

---

## Quick Start

1. Open `artifacts/excel/Coherence_Prompt_OS_v2.xlsx`
2. Review the `DASHBOARD_V2` tab for current KPI summary
3. Add decisions to `DECISION_LOG` — PriorityScore computes automatically
4. Add supporting claims to `ATOMIC_CLAIMS` — CredibilityScore computes automatically
5. Track assumptions in `ASSUMPTIONS` — ExpiryRisk colors automatically
6. When drift is detected, log it in `PATCH_LOG`
7. Run an LLM session using `prompts/prompt_os/START_SESSION_A1.md` and paste the output into `LLM_OUTPUT`
8. Snapshot weekly KPIs into `DASHBOARD_TRENDS`

---

## How to Integrate (Power Automate)

The workbook is designed for automation via Power Automate / Power Platform:

- **Ingest**: Email/Teams messages → `ATOMIC_CLAIMS` rows
- **Capture**: Meeting notes → `DECISION_LOG` entries
- **Monitor**: Scheduled weekly run → flag expired assumptions + drift prompts
- **Export**: Sealed snapshot (PDF + JSON) for audit trail

See [POWER_AUTOMATE_MAPPINGS.md](POWER_AUTOMATE_MAPPINGS.md) for exact table-to-column mapping.

---

## Related Docs

- [TABS_AND_SCHEMA.md](TABS_AND_SCHEMA.md) — Full column-level schema for every tab
- [SCORING.md](SCORING.md) — Formula documentation
- [POWER_AUTOMATE_MAPPINGS.md](POWER_AUTOMATE_MAPPINGS.md) — Automation integration mappings
- [diagrams/prompt_os_flow.mmd](diagrams/prompt_os_flow.mmd) — Architecture diagram
