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
Five executable domain modules wire core primitives into automated pipelines:
- **IntelOps** (12 handlers): claim lifecycle — ingest → validate → drift → patch → MG update
- **FranOps** (12 handlers): canon enforcement — propose → bless → enforce → retcon → propagate
- **ReflectionOps** (12 handlers): gate enforcement — episodes → gates → severity → audit → killswitch
- **AuthorityOps** (19 handlers): authority enforcement — action intake → actor/resource resolve → policy → DLR → assumptions → blast radius + simulation → decision gate → audit → drift detection
- **ParadoxOps** (12 handlers): paradox tension detection — tension sets → dimensions → pressure → drift promote → lifecycle
- **DecisionSurface**: portable Coherence Ops runtime with pluggable adapters (notebook, CLI, Vantage)
- **Cascade Engine**: 13 cross-domain rules with depth-limited propagation
- **Event Contracts**: routing table mapping 67 functions + 79 events to FEEDS topics

Every handler returns a `FunctionResult` with a deterministic `replay_hash` (SHA-256).

## What OVERWATCH is not
- Not a workflow engine
- Not a data platform
- Not an agent framework

It governs them.
