---
title: "Coherence Scoring Model"
version: "0.3.0"
status: "Living Document"
last_updated: "2026-02-16"
source_of_truth: "core/scoring.py"
---

# Coherence Scoring Model

**What:** A single 0–100 score that quantifies how coherent an organization's decision infrastructure is — across truth, reasoning, drift control, and memory.

**So What:** When the score drops, you know *which layer* is degrading and *why*, without reading code. When it rises, you can prove the fix worked.

> This documents current behavior; code is source of truth.
> > See `core/scoring.py` for the canonical implementation.
> >
> > ---
> >
> > ## How the Score Works
> >
> > The coherence score is a **weighted sum of four dimension scores**, each scored 0–100:
> >
> > | Dimension | Weight | Source Artifact | What It Measures |
> > |-----------|--------|-----------------|------------------|
> > | **Policy Adherence** | 0.25 | DLR (Decision Ledger Record) | Fraction of episodes with valid policy stamps |
> > | **Outcome Health** | 0.30 | RS (Reflection Session) | Blend of success rate (60%) and verification pass rate (40%) |
> > | **Drift Control** | 0.25 | DS (Drift Signal Collector) | Penalty-based: red severity, recurring patterns, total signal volume |
> > | **Memory Completeness** | 0.20 | MG (Memory Graph) | Episode node coverage vs. expected count from DLR |
> >
> > **Overall Score** = Σ (dimension_score × weight)
> >
> > ---
> >
> > ## Grade Thresholds
> >
> > | Score Range | Grade |
> > |-------------|-------|
> > | 90–100 | **A** |
> > | 75–89 | **B** |
> > | 60–74 | **C** |
> > | 40–59 | **D** |
> > | 0–39 | **F** |
> >
> > ---
> >
> > ## Dimension Details
> >
> > ### Policy Adherence (DLR) — Weight: 0.25
> >
> >     score = (episodes_with_policy_stamp / total_episodes) × 100
> >
> > Each episode's `policy` field is extracted as the DLR policy stamp. If all episodes carry a policy stamp, the score is 100. If no DLR data is present, the dimension defaults to 50 (neutral).
> >
> > ### Outcome Health (RS) — Weight: 0.30
> >
> >     score = (success_rate × 0.6 + verification_pass_rate × 0.4) × 100
> >
> > - `success_rate` = episodes with `outcome.code == "success"` / total episodes
> > - - `verification_pass_rate` = episodes where `verification.result == "pass"` / episodes with a verification result (excludes "na")
> >  
> >   - If no RS data is present, defaults to 50.
> >  
> >   - ### Drift Control (DS) — Weight: 0.25
> >  
> >   -     penalty = (red_count × 15) + (recurring_patterns × 10) + (total_signals × 2)
> >   -     score   = max(0, 100 − min(100, penalty))
> >
> >   - - `red_count` = number of drift signals with `severity: red`
> >     - - `recurring_patterns` = number of unique fingerprints that appear more than once
> >       - - `total_signals` = total drift events ingested
> >        
> >         - If no drift signals exist, the score is 100 (perfect — no drift detected).
> >        
> >         - ### Memory Completeness (MG) — Weight: 0.20
> >        
> >         -     score = min(100, (episode_nodes_in_graph / expected_episodes) × 100)
> >
> > - `episode_nodes_in_graph` = count of nodes with kind "episode" in the Memory Graph
> > - - `expected_episodes` = count of DLR entries
> >  
> >   - If no MG data exists, score is 0. If MG exists but no DLR baseline for comparison, score is 50.
> >  
> >   - ---
> >
> > ## Worked Example: Money Demo (Drift → Patch Cycle)
> >
> > Source: `python -m core.examples.drift_patch_cycle`
> >
> > Input: 3 sample episodes (`core/examples/sample_episodes.json`):
> >
> > | Episode | Outcome | Verification | Policy | Degrade |
> > |---------|---------|-------------|--------|---------|
> > | ep-demo-001 (deploy) | success | pass | present | none |
> > | ep-demo-002 (scale) | success | pass | present | none |
> > | ep-demo-003 (rollback) | partial | fail | present | safe_subset |
> >
> > ### State 1 — BASELINE (sealed, no drift)
> >
> > | Dimension | Score | Calculation | Weight | Contribution |
> > |-----------|-------|-------------|--------|-------------|
> > | Policy Adherence | 100.00 | 3/3 stamped | 0.25 | 25.00 |
> > | Outcome Health | 66.67 | (0.667 × 0.6 + 0.667 × 0.4) × 100 | 0.30 | 20.00 |
> > | Drift Control | 100.00 | no signals → no penalty | 0.25 | 25.00 |
> > | Memory Completeness | 100.00 | 3/3 episode nodes | 0.20 | 20.00 |
> > | **Overall** | | | | **90.00 (A)** |
> >
> > Outcome Health is 66.67 because 2 of 3 episodes succeed (success_rate = 0.667) and 2 of 3 verifications pass (pass_rate = 0.667). The 0.6/0.4 blend produces 66.67.
> >
> > ### State 2 — DRIFT (one red bypass signal injected)
> >
> > A single drift event is injected: `driftType: bypass`, `severity: red`, fingerprint `bypass-gate-cycle`.
> >
> > | Dimension | Score | Calculation | Weight | Contribution |
> > |-----------|-------|-------------|--------|-------------|
> > | Policy Adherence | 100.00 | unchanged | 0.25 | 25.00 |
> > | Outcome Health | 66.67 | unchanged | 0.30 | 20.00 |
> > | Drift Control | **83.00** | penalty: 1×15 + 0×10 + 1×2 = 17 | 0.25 | **20.75** |
> > | Memory Completeness | 100.00 | unchanged | 0.20 | 20.00 |
> > | **Overall** | | | | **85.75 (B)** |
> >
> > **What changed:** Drift Control dropped 100 → 83.
> >
> > - Red penalty: 1 signal × 15 = 15
> > - - Recurring penalty: 0 (the fingerprint appears only once, threshold is >1)
> >   - - Volume penalty: 1 signal × 2 = 2
> >     - - Total penalty: 17 → score 83
> >      
> >       - Overall drops 90.00 → 85.75. Grade drops A → B.
> >      
> >       - ### State 3 — PATCH (drift resolved via RETCON)
> >      
> >       - The drift is resolved. Pipeline re-runs with zero active drift signals. The Memory Graph gains the drift node, patch node, and a `resolved_by` edge — proving the correction.
> > 
| Dimension | Score | Calculation | Weight | Contribution |
|-----------|-------|-------------|--------|-------------|
| Policy Adherence | 100.00 | unchanged | 0.25 | 25.00 |
| Outcome Health | 66.67 | unchanged | 0.30 | 20.00 |
| Drift Control | 100.00 | no active signals | 0.25 | 25.00 |
| Memory Completeness | 100.00 | unchanged | 0.20 | 20.00 |
| **Overall** | | | | **90.00 (A)** |

Score restored. Grade restored. The Memory Graph diff contains:

- Added nodes: `drift-cycle-001`, `patch-cycle-001`
- - Added edge: `[drift-cycle-001, resolved_by, patch-cycle-001]`
 
  - ---

  ## Key Takeaways

  - **Drift Control is the most volatile dimension.** A single red signal drops the overall score by 4.25 points (from 25.00 to 20.75 contribution). Multiple red signals or recurring patterns compound rapidly.
  - - **Outcome Health carries the highest weight** (0.30). Sustained poor outcomes or failing verifications drag the score hardest over time.
    - - **Memory Completeness rewards graph coverage.** Orphaned episodes (present in DLR but missing from MG) reduce the score proportionally.
      - - **Scores are deterministic.** Same inputs always produce the same score. The Money Demo pins timestamps for byte-identical output across runs.
        - - **Patch restores the score** by eliminating active drift signals. The Memory Graph retains the drift-and-patch history for provenance — nothing is erased.
         
          - ---

          > This documents current behavior; code is source of truth.
          > > Implementation: [`core/scoring.py`](../core/scoring.py)
