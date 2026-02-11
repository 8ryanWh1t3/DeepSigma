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

## What RAL is not
- Not a workflow engine
- Not a data platform
- Not an agent framework

It governs them.
