---
title: "End-to-End Demo Walkthrough"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# End-to-End Demo: Decision > Seal > Drift > Patch > Memory

Time to complete: ~5 minutes reading. Scenario: quarantining a risky account.

## The Scenario

Two episodes: Episode 1 (ideal path, all data fresh) and Episode 2 (stale credit score triggers degradation, drift, and patch).

## Phase 1: DECIDE (Episode 1 — Ideal Path)

Three claims collected, all within TTL:

| Claim | Confidence | Age | TTL | Status |
|-------|------------|-----|-----|--------|
| Credit score 542 | 0.92 | 1.0s | 30s | GREEN |
| 3 failed payments | 0.98 | 2.0s | 60s | GREEN |
| Geo risk MEDIUM | 0.75 | 5.1s | 30s | AMBER |

Action: quarantine_account on account:A-1042. Verification: read_after_write PASSED.

## Phase 2: SEAL (Episode 1)

Episode sealed with SHA-256 hash. DLR extracted. No drift detected. Stored in Memory Graph.

## Phase 3: DRIFT (Episode 2 — Degraded Path)

45 minutes later, Account B-2091. Credit score is 35 seconds old vs 30s TTL — STALE. System degrades to cache_bundle.

After sealing, Drift Detector emits:
- driftType: freshness
- - severity: red (3rd occurrence in 24h)
  - - fingerprint: freshness/ttl-breach-credit-score
    - - recommendedPatchType: ttl_change
     
      - ## Phase 4: PATCH
     
      - Patch proposed: increase credit_score TTL from 30000ms to 60000ms. Severity is red so goes to human review. Ops team approves. DTE updated to v2.2.
     
      - ## Phase 5: MEMORY UPDATE
     
      - Memory Graph updated with new nodes (Episode, DriftSignal, Patch) and edges (TRIGGERED, PATCHED_BY, GROUNDED_IN).
     
      - IRIS query "Why did we quarantine B-2091?" returns full provenance chain.
     
      - ## Run It
     
      - ```bash
        # Clone and install
        git clone https://github.com/8ryanWh1t3/DeepSigma.git
        cd DeepSigma && pip install -r requirements.txt

        # Run the coherence demo
        PYTHONPATH=. python -m coherence_ops demo

        # Query with IRIS
        PYTHONPATH=. python -m coherence_ops iris query --type WHY --target ep-001
        ```

        ## The Loop is Complete

        DECIDE > SEAL > DRIFT > PATCH > MEMORY UPDATE > next decision uses updated policy.

        This is Institutional Decision Infrastructure. Decisions get sealed, monitored for drift, patched when they break, and remembered so the institution learns.

        ## Files Referenced

        | File | Purpose |
        |------|---------|
        | examples/sample_decision_episode_001.json | Full JSON for both episodes |
        | canonical/prime_constitution.md | Governance document |
        | canonical/dlr_spec.md | DLR data model |
        | canonical/ds_spec.md | Drift Signal spec |
        | canonical/mg_spec.md | Memory Graph spec |
        | runtime/encode_episode.md | How to encode |
        | runtime/drift_patch_workflow.md | How drift triggers patch |
        | runtime/sealing_protocol.md | How sealing works |
