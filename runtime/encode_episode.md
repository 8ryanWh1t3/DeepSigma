---
title: "How to Encode a Decision Episode"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# How to Encode a Decision Episode

## Prerequisites

- A Decision Timing Envelope (DTE) for the decision type
- - One or more AtomicClaims
  - - An Action Contract if the decision involves external effects
   
    - ## Steps
   
    - 1. **Load DTE** — defines deadline, stage budgets, TTL defaults, degrade ladder
      2. 2. **Gather Claims** — collect inputs, record capturedAt/confidence/statusLight/ttlMs; run TTL gate
         3. 3. **Reason** — build rationale graph, select action plan; degrade if any claim is stale
            4. 4. **Act** — dispatch action via Action Contract (blast radius, idempotency, rollback, auth)
               5. 5. **Verify** — run post-condition check (read-after-write, invariant, postcondition)
                  6. 6. **Seal** — compute SHA-256 hash over canonical JSON; episode becomes immutable
                     7. 7. **Extract DLR** — build Decision Log Record from sealed episode
                        8. 8. **Check for Drift** — if any anomaly detected, emit Drift Signal automatically
                          
                           9. ## Output
                          
                           10. A sealed DecisionEpisode JSON conforming to specs/episode.schema.json.
                          
                           11. See examples/sample_decision_episode_001.json for a complete example and examples/demo_walkthrough.md for a step-by-step guide.
