# Money Demo v2 — End-to-End Domain Mode Exercise

> One command. Ten steps. Three domains. Full governance loop with before/after metrics.

## Overview

The Money Demo v2 is a 10-step pipeline that exercises all three domain modes (IntelOps, FranOps, ReflectionOps) plus the cascade engine. It ingests baseline claims, introduces a contradicting delta, detects drift, executes a retcon, propagates cascades, runs coherence checks, and seals the episode.

**Run it**: `make demo-money` or `python -m enterprise.src.demos.money_demo`

**Module**: `enterprise/src/demos/money_demo/pipeline.py`

## Pipeline Steps

| Step | Name | Domain | What Happens |
|------|------|--------|-------------|
| 1 | LOAD | — | Load baseline (3 claims) + delta (1 contradicting claim) from fixtures |
| 2 | INTELOPS INGEST | IntelOps | Ingest all baseline claims via INTEL-F01 |
| 3 | INTELOPS VALIDATE | IntelOps | Validate all claims via INTEL-F02 |
| 4 | INTELOPS DELTA | IntelOps | Ingest contradicting claim, detect drift (INTEL-F01 -> F02 -> F03) |
| 5 | FRANOPS PROPOSE | FranOps | Propose and bless canon entries (FRAN-F01 -> F02) |
| 6 | FRANOPS RETCON | FranOps | Assess and execute retcon on contradicted claim (FRAN-F04 -> F05) |
| 7 | REOPS EPISODE | ReflectionOps | Begin episode, evaluate gates, attest non-coercion, seal (RE-F01 -> F04 -> F07 -> F02) |
| 8 | CASCADE | Cascade | Propagate retcon event through cross-domain rules |
| 9 | COHERENCE | ReflectionOps | Severity scoring (RE-F08) + coherence check (RE-F09) |
| 10 | SEAL | — | Compute summary with audit chain verification |

## Fixture Data

### Baseline (`fixtures/baseline.json`)

Three claims about a fictional ML churn prediction model:
- CLAIM-MONEY-001: Churn model accuracy (92%)
- CLAIM-MONEY-002: Churn model deployment readiness
- CLAIM-MONEY-003: Data pipeline freshness

### Delta (`fixtures/delta.json`)

One contradicting claim:
- CLAIM-MONEY-004: Churn model v3 underperforms on 2026 data (78% vs claimed 92%)

This triggers contradiction detection, drift signals, and a retcon of CLAIM-MONEY-002.

## Output Metrics (MoneyDemoResult)

| Metric | Description |
|--------|-------------|
| `baselineClaims` | Number of baseline claims loaded |
| `deltaClaims` | Number of delta claims loaded |
| `driftSignalsTotal` | Total drift signals detected across all steps |
| `retconExecuted` | Whether the retcon completed successfully |
| `cascadeRulesTriggered` | Number of cascade rules that fired |
| `coherenceScore` | Final coherence score |
| `episodeSealed` | Whether the episode was sealed |
| `auditEntries` | Total entries in the hash-chained audit log |
| `elapsedMs` | Pipeline execution time in milliseconds |

## Infrastructure Initialized

The pipeline creates:
- `IntelOps`, `FranOps`, `ReflectionOps` domain mode instances
- `CascadeEngine` with all three domains registered
- `MemoryGraph` for claim/drift/patch nodes
- `DriftSignalCollector` for drift ingestion
- `EpisodeTracker` for episode state management
- `CanonWorkflow` for canon state machine
- `AuditLog` for hash-chained non-coercion logging

## Deterministic Verification

Every handler call returns a `FunctionResult` with a `replay_hash` (SHA-256 of deterministic output fields). The demo can be replayed to verify identical outputs.

## CI Integration

`tests/test_money_demo_v2.py` runs the full pipeline as a regression test:
- Verifies all 10 steps complete
- Checks retcon executed
- Checks episode sealed
- Validates audit chain integrity
- Asserts coherence score is within expected range

## Related Pages

- [IntelOps](IntelOps) — claim lifecycle domain
- [FranOps](FranOps) — canon enforcement domain
- [ReflectionOps](ReflectionOps) — gate enforcement domain
- [Cascade Engine](Cascade-Engine) — cross-domain propagation
- [Event Contracts](Event-Contracts) — routing table
