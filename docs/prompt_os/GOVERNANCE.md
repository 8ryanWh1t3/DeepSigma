# Prompt OS v2 — Governance Policy

Governance rules for operating the Prompt OS workbook: ownership, review cadence, seal policy, and retention.

---

## Ownership

| Tab | Owner Role | Responsibility |
|-----|-----------|----------------|
| DECISION_LOG | Decision Owner (per row) | Log decisions, review on schedule |
| ATOMIC_CLAIMS | Any contributor | Add claims with source attribution |
| ASSUMPTIONS | Decision Owner (linked) | Set half-life, review on YELLOW/RED |
| PATCH_LOG | Patch Owner (per row) | Triage, resolve, or escalate patches |
| PROMPT_LIBRARY | Prompt Owner (per row) | Monitor health, flag drift, version updates |
| LLM_OUTPUT | Session Operator | Run triage, record output, apply updates |
| DASHBOARD_V2 | System (formulas) | No manual edits — read-only summary |
| DASHBOARD_TRENDS | Weekly Reviewer | Snapshot KPIs at end of each week |

---

## Review Cadence

| Activity | Frequency | Owner |
|----------|-----------|-------|
| Log new decisions | As they occur | Decision makers |
| Add claims / evidence | As they surface | Any contributor |
| Check assumption ExpiryRisk | Daily (glance) | Decision owners |
| Review YELLOW assumptions | Within the week | Linked decision owner |
| Review RED assumptions | Immediately | Linked decision owner |
| Triage open patches | Weekly | Patch owners |
| Run LLM triage session | Weekly | Designated operator |
| Snapshot dashboard trends | Weekly | Weekly reviewer |
| Full system review | Monthly | System owner |

---

## When to Create a Patch

Create a `PATCH_LOG` entry when:

1. An assumption reaches **RED** ExpiryRisk (expired past half-life)
2. A claim's **CredibilityScore drops below 40** (unreliable)
3. A prompt's **DriftFlag changes to "Major"** (output misalignment)
4. New counter-evidence **invalidates a prior claim** used in a decision
5. External conditions change and a decision's basis is no longer valid

---

## When to Expire an Assumption

Mark an assumption as `Expired` or `Invalidated` when:

- The **ExpiryRisk is RED** and review confirms the assumption no longer holds
- The **DisconfirmSignal** has been observed (the thing that would prove it wrong happened)
- The linked decision has been **Closed** or **Superseded**
- A **patch has been resolved** that addressed the assumption's failure

Do NOT delete expired assumptions — they are part of the institutional record.

---

## The Core Rule

> **No overwrite. Seal → Version → Patch.**

- Never overwrite a decision, claim, or assumption in-place
- If something changes, create a **new version** or a **patch**
- LLM session outputs are **sealed** — once recorded, they are immutable
- The workbook is a **ledger**, not a scratchpad

This rule ensures:
- Full audit trail of what was known and when
- Traceability from decision → evidence → assumption → patch
- Reproducibility of any past system state via sealed snapshots

---

## Escalation

| Condition | Action |
|-----------|--------|
| RED patch open > 7 days | Escalate to system owner |
| > 3 RED assumptions simultaneously | Schedule emergency review |
| LLM triage confidence < 50% | Re-run with fresh data; consider manual review |
| Workbook formula errors | Contact system owner; do not manually override |

---

## Seal Policy

Sealed runs create an immutable record of a point-in-time system state.

### When to Seal

| Trigger | Required? | Notes |
|---------|-----------|-------|
| Weekly LLM triage session | **Required** | Every triage run must produce a sealed output in `LLM_OUTPUT` |
| Before major decision (BlastRadius ≥ 4) | **Required** | Seal the system state before and after the decision |
| Monthly full system review | **Required** | Sealed snapshot for compliance archive |
| Ad-hoc governance audit | Recommended | Seal on request from leadership or compliance |
| After resolving a RED patch | Recommended | Seal to record the corrected state |

### Seal Contents

A sealed run includes:
- All named table data (JSON export)
- SHA-256 hash of the combined JSON
- Timestamp and operator identity
- Summary confidence percentage
- Next review date

### Seal Integrity

- Once a `SealHash` is written to `LLM_OUTPUT`, it is **immutable** — never overwrite
- If a correction is needed, create a **new LLM_OUTPUT row** with an updated seal
- Seal hashes should be verifiable: retain the source JSON alongside the hash

---

## Retention Policy

| Artifact | Retention | Storage |
|----------|-----------|---------|
| Workbook (live) | Current + rolling | Shared drive (SharePoint / OneDrive) |
| Sealed snapshots (JSON + PDF) | **12 months minimum** | Archive folder with read-only access |
| LLM_OUTPUT rows | Indefinite (part of workbook) | Retained in workbook as permanent record |
| DASHBOARD_TRENDS rows | Indefinite | Retained in workbook — do not prune |
| Expired assumptions | Indefinite | Retained in workbook — mark `Expired`, do not delete |
| Resolved patches | Indefinite | Retained in workbook — mark `Resolved`, do not delete |
| Superseded decisions | Indefinite | Retained in workbook — mark `Superseded`, do not delete |

### Retention Rules

1. **Never delete rows** from any table — the workbook is an append-only ledger
2. **Sealed snapshots** must be retained for at least 12 months for audit trail compliance
3. **Monthly archive**: at each monthly review, export a sealed snapshot to the archive folder
4. **Access control**: archive folder should be read-only for all users except the system owner
5. **Naming convention**: sealed snapshots use `YYYY-MM-DD_sealed_snapshot.json` format
