---
title: "PRIME Constitution — Truth · Reasoning · Memory"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
spec_id: "PRIME-CONST-001"
---

# PRIME Constitution

## Purpose

**What:** The PRIME Constitution is the foundational document for Institutional Decision Infrastructure. It defines the three invariants that every decision must satisfy and the governance loop that enforces them across time.

**So What:** Without this constitution, decision systems become "log and pray" — they record what happened but cannot prove *why*, cannot detect *drift*, and cannot *learn*. This constitution makes decisions auditable, correctable, and institutional.

## The Three Invariants

### 1. Truth

Every decision must be grounded in claims that were **true and fresh at decision time**.

Rules:
- Every input to a decision must be an `AtomicClaim` with `confidence`, `statusLight`, `halfLife`, and `evidence`.
- - Claims have TTL (time-to-live). A claim past its TTL is **stale** and must not be used without degradation.
  - - Truth is not binary. Claims carry `confidence` (0.0-1.0) and `truthType` (empirical | derived | asserted | policy | inferred).
    - - The system must record `capturedAt` timestamps for every claim used in a decision.
     
      - ### 2. Reasoning
     
      - Every decision must be explainable: **what policy applied, what alternatives existed, and why this path was chosen**.
     
      - Rules:
      - - Every decision must reference a Decision Timing Envelope (DTE) that defines its deadline, budget, TTL gate, and degrade ladder.
        - - If the ideal path cannot be taken (stale data, timeout, unsafe action), the system must follow the degrade ladder: `cache_bundle > small_model > rules_only > hitl > abstain > bypass`.
          - - The chosen degrade step and its rationale must be recorded.
            - - Action contracts must declare blast radius, idempotency, rollback, and authorization mode.
             
              - ### 3. Memory
             
              - Every decision must be **sealed, immutable, and queryable** — forming institutional memory that persists across time.
             
              - Rules:
              - - Every completed decision produces a sealed `DecisionEpisode` with a `sealHash` (SHA-256), `sealedAt` timestamp, and `version`.
                - - Sealed episodes are immutable. Changes produce new versions with `patch_log` entries.
                  - - The Memory Graph (MG) links episodes, actions, drift signals, and patches via typed provenance edges.
                    - - Any operator must be able to answer "why did we do this?" in under 60 seconds via the IRIS query engine.
                     
                      - ## The Governance Loop
                     
                      - ```
                        TRUTH (claims, TTL, evidence)
                            |
                        REASONING (DTE, degrade, action contract, verify)
                            |
                        MEMORY (seal, DLR, RS, DS, MG)
                            |
                        DRIFT (detected anomaly — stale TTL, deadline miss, verify fail)
                            |
                        PATCH (corrective change — recorded with provenance)
                            |
                        MEMORY UPDATE (MG absorbs patch, RS learns, next decision improves)
                            |
                        TRUTH (refreshed claims for next decision)
                        ```

                        This loop is continuous. It does not require human intervention to detect drift or propose patches, but it **does** require human review for patches above a configurable severity threshold.

                        ## The Four Artifacts

                        The constitution materializes through four canonical artifacts:

                        | Artifact | Maintains | Constitution Link |
                        |----------|-----------|-------------------|
                        | **DLR** (Decision Log Record) | The "truth receipt" — what policy governed, what claims supported, what was verified | Truth + Reasoning |
                        | **RS** (Reflection Session) | The "learning journal" — what happened, what degraded, what to improve | Reasoning + Memory |
                        | **DS** (Drift Signal) | The "alarm" — what is breaking, how badly, how to fix it | Truth (decaying) |
                        | **MG** (Memory Graph) | The "institutional brain" — provenance graph linking all decisions, actions, drift, patches | Memory |

                        See individual specs: [dlr_spec.md](dlr_spec.md) | [rs_spec.md](rs_spec.md) | [ds_spec.md](ds_spec.md) | [mg_spec.md](mg_spec.md)
