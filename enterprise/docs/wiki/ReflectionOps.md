# ReflectionOps — Gate Enforcement & Episode Completeness

> Every decision gets an episode. Every episode gets a seal. Every seal proves what happened.

## Overview

ReflectionOps is the gate enforcement domain. It wraps RuntimeGate, CoherenceGate, ReflectionSession, IRISEngine, degrade ladder, episode state machine, audit log, and kill-switch into 12 function handlers keyed by `RE-F01` through `RE-F12`.

**Module**: `src/core/modes/reflectionops.py`

## Function Map

| ID | Name | Purpose |
|----|------|---------|
| RE-F01 | `episode_begin` | Begin a new decision episode, transition to ACTIVE |
| RE-F02 | `episode_seal` | Seal an active episode with hash chain |
| RE-F03 | `episode_archive` | Archive a sealed episode to cold storage |
| RE-F04 | `gate_evaluate` | Evaluate RuntimeGate constraints |
| RE-F05 | `gate_degrade` | Apply a degrade step from the degrade ladder |
| RE-F06 | `gate_killswitch` | Activate kill-switch: freeze all episodes |
| RE-F07 | `audit_non_coercion` | Log non-coercion attestation (hash-chained) |
| RE-F08 | `severity_score` | Compute centralized severity score |
| RE-F09 | `coherence_check` | Run coherence gate evaluation with domain context |
| RE-F10 | `reflection_ingest` | Ingest a sealed episode into the reflection session |
| RE-F11 | `iris_resolve` | Resolve an IRIS query (WHY, WHAT_CHANGED, STATUS) |
| RE-F12 | `episode_replay` | Deterministically replay a sealed episode and verify hash match |

## Episode State Machine

```
PENDING -> ACTIVE -> SEALED -> ARCHIVED
                       |
                       +--[freeze]--> FROZEN
```

**Implementation**: `src/core/episode_state.py`

## Core Episode Flow

```
RE-F01 (begin) -> RE-F04 (gate evaluate) -> RE-F07 (non-coercion)
                                               |
                                               v
             RE-F03 (archive) <- RE-F02 (seal) <- RE-F09 (coherence)
```

## Kill-Switch (RE-F06)

Emergency mechanism that:
1. **Freezes** all in-flight episodes (ACTIVE -> FROZEN)
2. **Emits halt proof** bundle (who authorized, why, timestamp)
3. **Publishes** `drift_signal` with subtype `killswitch_activated`, severity `red`
4. **Resume** requires explicit authority check

**Implementation**: `src/core/killswitch.py`

## Non-Coercion Audit Log (RE-F07)

Append-only, hash-chained NDJSON log. Each entry links to the previous via SHA-256, creating a tamper-evident chain. The log records gate evaluations, degrade steps, episode seals, and non-coercion attestations.

**Implementation**: `src/core/audit_log.py`

## Severity Scoring (RE-F08)

Centralized severity scorer called by all domains. Takes drift type, current severity, and context (recurrence count). Returns a numeric score and classification (green/yellow/red).

**Implementation**: `src/core/severity.py`

## Coherence Check (RE-F09)

Heuristic based on drift signal count:
- 0 drift signals: 95.0 (green)
- 1-3 drift signals: 70.0 (yellow)
- 4+ drift signals: 40.0 (red)

Emits `coherence_{signal}` event. Non-green results generate drift signals.

## Deterministic Replay (RE-F12)

Replays a sealed episode by recomputing from episode data. Compares SHA-256 hash against expected value. Hash mismatch emits a red-severity `process_gap` drift signal.

## Cascade Interactions

ReflectionOps is a **target** for:
- CASCADE-R03: FranOps retcon executed -> RE-F01 episode flag
- CASCADE-R07: Any red-severity drift -> RE-F08 severity scoring

ReflectionOps is a **source** for:
- CASCADE-R05: Episode freeze -> IntelOps half-life check (INTEL-F11)
- CASCADE-R06: Kill-switch -> self-propagation (RE-F06)

## Context Dependencies

| Key | Type | Used By |
|-----|------|---------|
| `episode_tracker` | EpisodeTracker | F01, F02, F03, F06 |
| `memory_graph` | MemoryGraph | F01, F09 |
| `drift_collector` | DriftSignalCollector | F09 |
| `audit_log` | AuditLog | F02, F04, F05, F07, F12 |
| `gates` | list | F04 |
| `coherence_score` | float | F09 (optional override) |
| `reflection_session` | ReflectionSession | F10 |
| `iris_engine` | IRISEngine | F11 |

## Related Pages

- [Sealing and Episodes](Sealing-and-Episodes) — immutability model
- [IntelOps](IntelOps) — claim lifecycle domain
- [FranOps](FranOps) — canon enforcement domain
- [Cascade Engine](Cascade-Engine) — cross-domain propagation
- [Event Contracts](Event-Contracts) — routing table and event declarations
- [IRIS](IRIS) — operator query engine
