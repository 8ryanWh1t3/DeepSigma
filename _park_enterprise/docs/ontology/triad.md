---
title: "The Triad — Truth · Reasoning · Memory"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# The Triad: Truth · Reasoning · Memory

## Truth

Truth is the set of claims that were believed to be valid at the moment a decision was made. Truth is not absolute — it is scoped, confidence-weighted, time-bounded, and evidence-linked.

Properties of Truth in this system:

- **Atomic:** The smallest unit is the `AtomicClaim`.
- - **Temporal:** Every claim has `capturedAt`, `ttlMs`, and `halfLife`. Truth decays.
  - - **Evidenced:** Every claim links to its evidence sources.
    - - **Graded:** Confidence is a number (0.0-1.0), not a boolean.
      - - **Colored:** `statusLight` (GREEN/AMBER/RED) gives instant visual triage.
       
        - ## Reasoning
       
        - Reasoning is the process that transforms truth into action. It encompasses which policy applied, what alternatives were considered, why this specific path was chosen, and what constraints bounded the choice.
       
        - Properties of Reasoning in this system:
       
        - - **Governed:** Every decision class has a DTE that defines its rules of engagement.
          - - **Degradable:** When the ideal path is unavailable, the system follows a degrade ladder with documented rationale.
            - - **Contracted:** Actions carry explicit contracts — blast radius, idempotency, rollback, authorization.
              - - **Verified:** Post-conditions are checked, not assumed.
               
                - ## Memory
               
                - Memory is the institutional record of what happened, what was learned, and how the system changed as a result. It is not a log — it is a provenance graph that links decisions to their causes, consequences, and corrections.
               
                - Properties of Memory in this system:
               
                - - **Sealed:** Episodes are immutable once sealed. Changes create new versions.
                  - - **Linked:** The Memory Graph connects episodes, claims, drift, and patches via typed edges.
                    - - **Queryable:** The IRIS engine answers "why?" in under 60 seconds.
                      - - **Learning:** Reflection Sessions convert raw experience into institutional learning.
                        - - **Self-correcting:** The Drift to Patch loop feeds corrections back into the next decision.
