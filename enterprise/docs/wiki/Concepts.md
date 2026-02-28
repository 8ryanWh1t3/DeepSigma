# Concepts

## What problem does RAL solve?
Agents fail in production when they act on:
- **late** decisions (deadline misses, tail latency)
- **stale** context (TTL/TOCTOU)
- **unsafe** actions (no idempotency/rollback/auth)
- **unverified** outcomes (no postconditions)

RAL adds the missing runtime layer: **“await for reality.”**

## Core primitives
- **DTE (Decision Timing Envelope)**: time budgets and limits
- **Freshness gates**: timestamps + TTL + TOCTOU checks
- **Safe Action Contract**: blast radius, idempotency, rollback, authorization
- **Verification**: read-after-write, invariants, dual-run (optional)
- **Sealing**: immutable DecisionEpisode
- **Drift → Patch**: structured learning loop

## Domain Modes
Three executable domain modules wire core primitives into automated pipelines:
- **IntelOps** (12 handlers): claim lifecycle — ingest → validate → drift → patch → MG update
- **FranOps** (12 handlers): canon enforcement — propose → bless → enforce → retcon → propagate
- **ReflectionOps** (12 handlers): gate enforcement — episodes → gates → severity → audit → killswitch
- **Cascade Engine**: 7 cross-domain rules with depth-limited propagation
- **Event Contracts**: routing table mapping 36 functions + 39 events to FEEDS topics

Every handler returns a `FunctionResult` with a deterministic `replay_hash` (SHA-256).

## What RAL is not
- Not a workflow engine
- Not a data platform
- Not an agent framework

It governs them.
