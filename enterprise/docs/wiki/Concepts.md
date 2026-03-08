# Concepts

## What problem does Coherence Ops solve?
Agents fail in production when they act on:
- **late** decisions (deadline misses, tail latency)
- **stale** context (TTL/TOCTOU)
- **unsafe** actions (no idempotency/rollback/auth)
- **unverified** outcomes (no postconditions)

OVERWATCH adds the missing governance layer: **enforce coherence before, during, and after execution.**

## Core primitives
- **DTE (Decision Timing Envelope)**: time budgets and limits
- **Freshness gates**: timestamps + TTL + TOCTOU checks
- **Safe Action Contract**: blast radius, idempotency, rollback, authorization
- **Verification**: read-after-write, invariants, dual-run (optional)
- **Sealing**: immutable DecisionEpisode
- **Drift → Patch**: structured learning loop

## Domain Modes
Six executable domain modules wire core primitives into automated pipelines:
- **IntelOps** (12 handlers): claim lifecycle — ingest → validate → drift → patch → MG update
- **FranOps** (12 handlers): canon enforcement — propose → bless → enforce → retcon → propagate
- **ReflectionOps** (19 handlers): gate enforcement — episodes → gates → severity → audit → killswitch + institutional memory (precedent, fingerprint, knowledge consolidation, temporal recall, decay)
- **AuthorityOps** (19 handlers): authority enforcement — action intake → actor/resource resolve → policy → DLR → assumptions → blast radius + simulation → decision gate → audit → drift detection
- **ParadoxOps** (12 handlers): paradox tension detection — tension sets → dimensions → pressure → drift promote → lifecycle
- **ActionOps** (19 handlers): commitment tracking — intake → validate → deliverables → deadlines → risk → breach → escalation → remediation + decision accounting (cost, value, debt, ROI, budget)
- **DecisionSurface**: portable Coherence Ops runtime with pluggable adapters (notebook, CLI, Vantage)
- **Drift Radar**: cross-domain drift intelligence surface — correlation, trending, forecasting, remediation prioritization
- **Cascade Engine**: 27 cross-domain rules with depth-limited propagation
- **Event Contracts**: routing table mapping 79 functions + 91 events to FEEDS topics

Every handler returns a `FunctionResult` with a deterministic `replay_hash` (SHA-256).

## What OVERWATCH is not
- Not a workflow engine
- Not a data platform
- Not an agent framework

It governs them.
