# Prompt OS v2 — Governance Policy Card

Minimal governance rules for operating the Prompt OS workbook.

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
