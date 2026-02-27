# FAQ

## Is this task scheduling?
Not primarily. Schedulers decide **when** to run.
RAL decides **whether it’s safe to act now** and proves it.

## Does this compete with Foundry / Power Platform / LangChain?
No. It governs them.

## What’s the smallest thing I can run?
The one-command demo: `coherence demo` — produces BASELINE, DRIFT, and PATCH states in one invocation. Add `--json` for machine-readable output.

## What is the PRIME gate?

PRIME converts LLM probability gradients into APPROVE/DEFER/ESCALATE verdicts using Truth-Reasoning-Memory invariants. It governs the write path — every sealed episode passes through PRIME before becoming institutional memory. See [Concepts](Concepts) for details.

## What is the CoherenceGate?

A composable enforcement gate combining the 4-dimension CoherenceScorer (0-100) with the PRIME gate to produce a GREEN/YELLOW/RED signal. GREEN means all dimensions pass thresholds. YELLOW means at least one dimension is marginal. RED means a critical invariant is violated.

## What is IRIS?

Interface for Resolution, Insight, and Status — the operator-facing query engine. Five query types: WHY (trace a decision), WHAT_CHANGED (audit delta), WHAT_DRIFTED (drift summary), RECALL (full episode context), STATUS (coherence health check). All queries resolve in under 60 seconds with full provenance chains. See [IRIS](IRIS) for full docs.

## What is the authority ledger?

An append-only, hash-chained record of who authorized what. Each entry chains to the previous via `prev_entry_hash` (SHA-256), making the ledger tamper-evident. Supports direct grants, delegated authority, emergency overrides, and revocations. ABPs bind to specific ledger entries via `authority_ref`. See [Authority Ledger Binding](Authority-Ledger-Binding) for the full format.

## What is the FEEDS surface?

Federated Event Envelope Distribution Surface — a 5-stage event-driven pipeline connecting governance primitives (TS, ALS, DLR, DS, CE) via file-based pub/sub. Stages: (1) event envelope + schemas, (2) file-bus pub/sub + DLQ, (3) manifest-first ingest orchestrator, (4) consumers (authority gate, evidence check, triage), (5) canon store + claim validator + MG writer. All packets are SHA-256 hashed with two-phase validation.

## What are the SDK packages?

Three standalone pip-installable packages for framework integration:

| Package | Install | What it does |
| --- | --- | --- |
| `langchain-deepsigma` | `pip install langchain-deepsigma` | Exhaust + governance callbacks for LangChain and LangGraph |
| `deepsigma-middleware` | `pip install deepsigma-middleware` | `@log_decision` decorator, ASGI middleware, Flask extension |
| `openai-deepsigma` | `pip install openai-deepsigma` | Generic agent wrapper — logs intent, intercepts tool calls, detects drift |

All three integrate with `AgentSession` for sealed decision episodes.

## What is AgentSession?

A stateful facade over DLR, DriftSignal, MemoryGraph, and CoherenceScorer. Call `session.log_decision()` to record decisions, `session.detect_drift()` to find drift, `session.score()` for coherence scoring, and `session.prove()` for audit export.

## What metrics does the coherence CLI expose?

Four composable metric points via `coherence metrics`:

- **coherence_score** (0-100) — weighted composite of policy adherence, outcome health, drift control, and memory completeness
- **drift_density** (ratio) — drift signals per episode; lower is better
- **authority_coverage** (ratio) — fraction of claims with valid authority grants
- **memory_coverage** (ratio) — fraction of expected episodes in the memory graph

## Is there a demo site?

Yes. The static site lives at `docs/site/` and deploys to GitHub Pages on push to `main`. No JavaScript or build tooling — pure HTML/CSS with a terminal aesthetic. Run `make site-content` to regenerate the data files.

## What is the System Stability Index (SSI)?

A 0-100 composite metric that detects unsustainable KPI swings across releases. Formula: `SSI = 0.35*Volatility + 0.30*DriftAccel + 0.20*Authority + 0.15*Economic`. Gates: PASS >= 70, WARN >= 55, FAIL < 55. SSI penalizes large release-to-release KPI deltas (volatility) and accelerating drift (second derivative of KPI movements). Recovery requires multiple stable releases to dilute historical acceleration. See `enterprise/scripts/nonlinear_stability.py`.

## What is TEC sensitivity analysis?

An economic fragility assessment that measures how C-TEC costs shift when governance health factors (RCF from ICR, CCF from PCR) change by one tier. Outputs: cost volatility index (stddev/mean of tier costs), sensitivity bands, economic fragility score (0-100), and a human-readable report. Run via `make tec-sensitivity`.

## What is the security proof pack?

An integrity-chain-aware security report replacing the earlier stub gate. Checks four areas: (1) key lifecycle documentation (generation, rotation, revocation), (2) crypto proof script validity, (3) seal chain integrity (hash chain continuity), (4) contract fingerprint consistency. Outputs `security_proof_pack.json` and enriched `SECURITY_GATE_REPORT.md`. Run via `make security-gate`.

## What is the stale artifact kill-switch?

A CI gate that prevents stale or missing release artifacts from passing the pipeline. Five checks: version match, current-version radar exists, badge freshness, history appended, contract fingerprint match. Run via `make verify-release-artifacts`.

## How does the scalability benchmark work?

The re-encrypt benchmark (`make benchmark`) runs a deterministic 100K-record DISR pipeline with `--ci-mode`. It measures throughput (records/sec), wall clock time, CPU time, and peak RSS memory. In CI mode, it sets `kpi_eligible=true` and `evidence_level=real_workload`, which uncaps the scalability KPI from the 4.0 simulated ceiling. The benchmark also produces `benchmark_history.json` for trend analysis and regression detection.

## What is the scalability regression gate?

A CI gate (`make scalability-gate`) that compares the latest benchmark against the previous run. It enforces two rules: (1) throughput must stay above 80% of the previous benchmark, (2) evidence level must be `real_workload` or `ci_benchmark`. This prevents performance regressions from landing undetected. Report: `release_kpis/SCALABILITY_GATE_REPORT.md`.

## How does SSI recovery work?

SSI (System Stability Index) penalizes large release-to-release KPI swings. Historical oscillations in automation_depth (v2.0.3–v2.0.7) drove `drift_acceleration_score` to 0.0 (30% of SSI weight). Recovery requires multiple consecutive stable releases to dilute the acceleration average below the 1.0 threshold. v2.0.8 improved SSI from 37.71 to 39.05 by adding scalability evidence (+4.62) while holding all other KPIs stable. SSI >= 55 is projected around v2.1.0.

## What is the Reference Layer Manifesto?

The manifesto (`docs/manifesto.md`) defines three institutional failures that agentic AI creates — decision amnesia, authority vacuum, and silent drift — and the contract a reference layer must satisfy: intent explicit, authority verified, logic auditable, outcomes sealed.
