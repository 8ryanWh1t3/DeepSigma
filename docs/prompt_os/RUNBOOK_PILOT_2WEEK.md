# Prompt OS v2 — 2-Week Pilot Runbook

Minimal pilot plan for 5 users, 10 decisions, 2 weeks.

---

## Day 1: Setup (30 min)

- [ ] Open `artifacts/excel/Coherence_Prompt_OS_v2.xlsx` in shared location (SharePoint / OneDrive / local)
- [ ] Review `DASHBOARD_V2` tab — confirm formulas compute
- [ ] Assign pilot owner (single point of contact for questions)
- [ ] Share workbook with 5 pilot participants
- [ ] Walk team through tabs: DECISION_LOG → ATOMIC_CLAIMS → ASSUMPTIONS → PATCH_LOG → LLM_OUTPUT
- [ ] Log first decision together as a group exercise
- [ ] Add 2 supporting claims for that decision
- [ ] Register 1 assumption with a half-life estimate
- [ ] Confirm ExpiryRisk shows GREEN

---

## Daily Use (10 min/day)

- [ ] Log any new decisions made today in `DECISION_LOG`
- [ ] Add supporting claims to `ATOMIC_CLAIMS` when evidence surfaces
- [ ] Check `ASSUMPTIONS` tab — note any YELLOW or RED ExpiryRisk rows
- [ ] If an assumption expired (RED), open a `PATCH_LOG` entry

### Quick Reference

| Action | Tab | Time |
|--------|-----|------|
| Log a decision | DECISION_LOG | 3 min |
| Add a claim | ATOMIC_CLAIMS | 2 min |
| Check assumptions | ASSUMPTIONS | 2 min |
| Open a patch | PATCH_LOG | 3 min |

---

## Weekly Review (30 min — end of week)

### Week 1 Review

- [ ] Count decisions logged — target: ≥ 5
- [ ] Count claims captured — target: ≥ 10
- [ ] Review all YELLOW/RED assumptions — action or extend
- [ ] Run LLM triage session:
  1. Export workbook data (copy tabs or use CSV export)
  2. Use system prompt from `prompts/prompt_os/START_SESSION_A1.md`
  3. Paste LLM output into `LLM_OUTPUT` tab
  4. Apply any suggested updates
- [ ] Snapshot dashboard KPIs into `DASHBOARD_TRENDS`
- [ ] Note: What worked? What felt clunky?

### Week 2 Review

- [ ] Count total decisions — target: ≥ 10
- [ ] Verify at least 1 drift → patch cycle completed
- [ ] Run second LLM triage session
- [ ] Compare `DASHBOARD_TRENDS` week-over-week
- [ ] Capture pilot retro notes (below)

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Decisions logged | ≥ 10 | `COUNTIF(DecisionLogTable[Status],"Active")` |
| Claims captured | ≥ 15 | `COUNTA(AtomicClaimsTable[ClaimID])` |
| Drift → Patch cycles | ≥ 1 | Any `PatchLogTable` row with `Status = "Resolved"` |
| Median "why retrieval" | ≤ 60s | Time to find reasoning for a past decision |
| LLM triage sessions | ≥ 2 | `COUNTA(LLMOutputTable[RunID])` |
| Dashboard snapshots | ≥ 2 | `COUNTA(DashboardTrendsTable[WeekEnding])` |

---

## Stop Conditions

Stop the pilot early if:

- Team reports > 20 min/day overhead (should be ≤ 10)
- Workbook becomes unusable (formula errors, corruption)
- No decisions logged after 5 business days
- Team consensus that the system adds friction without value

---

## What to Capture in LLM_OUTPUT

Every LLM triage session should record:

| Field | What to Capture |
|-------|----------------|
| RunID | Sequential: `RUN-001`, `RUN-002`, ... |
| SessionDate | Date of the session |
| Model | Which LLM was used |
| TopActions | The 3 actions the LLM recommended |
| TopRisks | The 3 risks the LLM identified |
| SuggestedUpdates | Specific rows the LLM recommended updating |
| SealHash | Leave as placeholder unless using sealed export tool |
| SummaryConfidence_pct | LLM's self-assessed confidence |
| NextReviewDate | When to run next session |
| Operator | Who ran the session |

---

## Pilot Retro Template

After Week 2, answer:

1. What decisions would have been lost without this system?
2. Did any assumption expirations catch something real?
3. Was the LLM triage useful? What would make it better?
4. What's the right cadence going forward? (daily log + weekly review? something else?)
5. Should we expand to more users? What needs to change first?
