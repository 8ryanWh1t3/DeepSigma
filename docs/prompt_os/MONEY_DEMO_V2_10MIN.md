---
title: "Money Demo v2 — 10-Minute Live Walkthrough"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-21"
---

# Money Demo v2 — 10-Minute Live Walkthrough

**Audience:** Decision-makers evaluating Prompt OS for institutional adoption.
**Format:** Live demo with before/after delta framing.
**Goal:** Show that one 10-minute session produces measurable, auditable improvement.

---

## 1) Goal (20 seconds)

> "In the next 10 minutes, I'm going to take one real decision from your backlog, run it through Prompt OS, and show you exactly what changes — with numbers."

---

## 2) Setup (60 seconds)

1. Open `artifacts/excel/Coherence_Prompt_OS_v2.xlsx`
2. Open the sample CSV data set at `artifacts/sample_data/prompt_os_v2/`
3. Confirm the workbook has live data in `DECISION_LOG`, `ATOMIC_CLAIMS`, `ASSUMPTIONS`
4. Note the `DASHBOARD_V2` tab — this is the "before" snapshot

---

## 3) Before Snapshot (60 seconds)

Capture the current state from `DASHBOARD_V2`:

| KPI | Current Value |
|-----|---------------|
| Active Decisions | _read from dashboard_ |
| Avg Confidence | _read from dashboard_ |
| Expired Assumptions | _read from dashboard_ |
| Open RED Patches | _read from dashboard_ |
| Sealed Runs | _count in `artifacts/sealed_runs/`_ |

Screenshot or note these values. You will compare them in step 6.

---

## 4) Live Run (4 minutes)

### 4a. Run Executive prompt on 1 decision (~60s)

1. Pick a high-priority decision from `DECISION_LOG` (e.g. one with `PriorityScore >= 7`)
2. Copy the system prompt from `prompts/prompt_os/START_SESSION_A1.md`
3. Run your LLM with the workbook data attached
4. Paste the structured output into the `LLM_OUTPUT` tab

### 4b. Add 1 atomic claim (~30s)

1. Go to `ATOMIC_CLAIMS` tab
2. Add a new claim supporting or challenging the decision
3. Confirm `CredibilityScore` computes automatically

### 4c. Expire 1 assumption (~30s)

1. Go to `ASSUMPTIONS` tab
2. Find an assumption past its half-life (or manually set `ExpiryDate` to today)
3. Confirm `ExpiryRisk` turns RED

### 4d. Create 1 RED patch (~30s)

1. Go to `PATCH_LOG` tab
2. Add a new row: `TriggerType=Drift`, link to the expired assumption, `Severity_GYR=RED`
3. This is the system self-correcting

### 4e. Emit telemetry (~30s)

Run the hero loop to detect drift and emit telemetry:

```bash
python src/tools/prompt_os/drift_to_patch_demo.py --user "Demo"
```

### 4f. Export sealed JSON (~30s)

The hero loop already exported a sealed run. Verify:

```bash
ls artifacts/sealed_runs/
```

---

## 5) After Snapshot (60 seconds)

Re-read `DASHBOARD_V2` and `DASHBOARD_TRENDS`:

| KPI | After Value |
|-----|-------------|
| Active Decisions | _updated_ |
| Avg Confidence | _updated_ |
| Expired Assumptions | _+1_ |
| Open RED Patches | _+1_ |
| Sealed Runs | _+1_ |

---

## 6) Delta Slide (90 seconds)

Present the before/after delta:

| Metric | Before | After |
|---|---:|---:|
| High-risk decisions structured | 0 | 1 |
| Expired assumptions addressed | 0 | 1 |
| Drift→Patch cycles | 0 | 1 |
| Sealed run artifacts | 0 | 1 |
| "Why retrieval" time | ∞ | ≤60s |

**Key message:** In 10 minutes, you went from zero structured governance to one complete, sealed decision cycle with drift detection and a patch on record.

---

## 7) Close (30 seconds)

> "This took 10 minutes with sample data. Imagine 10 real decisions over 2 weeks. That's the pilot."

**Pilot ask:** 5 users, 2 weeks, 10 decisions.

---

## What the Exec Should Notice

- **Decisions have scores, not just titles.** PriorityScore surfaces what matters.
- **Assumptions expire.** The system flags stale reasoning before it causes damage.
- **Drift creates patches, not panic.** Self-correction is a first-class operation.
- **Everything is sealed.** JSON artifacts prove what was decided, by whom, and when.
- **Retrieval is instant.** "Why did we choose X?" has a structured answer in ≤60 seconds.

---

## Pilot Acceptance Criteria

- **10 decisions logged** with complete PriorityScore computation
- **≥3 drift→patch cycles** completed and sealed
- **"Why retrieval" time ≤60 seconds** for any logged decision

---

## Related

- [RUNBOOK_PILOT_2WEEK.md](RUNBOOK_PILOT_2WEEK.md) — Full 2-week pilot plan
- [EXECUTIVE_BRIEF_1PAGER.md](EXECUTIVE_BRIEF_1PAGER.md) — One-page executive brief
- [SEALED_RUN_EXPORT_SPEC.md](SEALED_RUN_EXPORT_SPEC.md) — Sealed run JSON format
