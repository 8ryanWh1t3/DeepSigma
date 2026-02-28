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

SSI (System Stability Index) penalizes large release-to-release KPI swings. Historical oscillations in automation_depth (v2.0.3–v2.0.7) drove `drift_acceleration_score` to 0.0 (30% of SSI weight). Recovery required multiple consecutive stable releases to dilute the acceleration average below the 1.0 threshold. Seven stability releases (v2.0.10–v2.0.16) shipped zero-drift KPI holds while closing 22 issues, driving SSI from 34.64 (v2.0.9) to 60.02 (v2.1.0) and drift_acceleration_index from 1.00 to 0.68. The SSI >= 55 gate is now satisfied.

## What is authority evidence?

The authority evidence export (`make authority-evidence`) produces `authority_evidence.json` — a release artifact summarizing the authority ledger state: entry count, chain integrity verification, grant/refusal breakdown, signing key IDs, and a SHA-256 verification hash. This provides auditable proof of the authority governance lifecycle.

## What are economic metrics?

The economic metrics artifact (`make economic-metrics`) produces `economic_metrics.json` by combining TEC pipeline data (hours, costs, decision counts) with security benchmark data (MTTR, throughput). It sets `kpi_eligible=true` and `evidence_level=real_workload`, which uncaps the economic_measurability KPI from the 4.0 simulated ceiling. Sources: `tec_internal.json`, `security_metrics.json`, `issues_all.json`.

## What is a refusal contract?

A refusal contract is an explicit authority action that blocks a specific action type. Created via `create_refusal_contract()`, it produces a `REFUSE:<action_type>` contract. The authority ledger records `AUTHORITY_REFUSAL` entries, and the FEEDS authority gate consumer checks for active refusals, emitting an `AUTHORITY_REFUSED` drift signal (severity red) when a refused action is attempted.

## Are all 8 KPIs passing?

Yes, since v2.0.9 and continuing through v2.1.0. The KPI gate requires all 8 axes >= 7.0. v2.0.9 lifted the final two blockers: authority_modeling (6.0 → 9.72 via P0 #325 closure + signature custody/refusal/evidence chain) and economic_measurability (4.88 → 10.0 via dedicated `economic_metrics.json` with `kpi_eligible=true`). v2.1.0 scores: technical_completeness=10, automation_depth=10, authority_modeling=9.72, enterprise_readiness=10, scalability=10, data_integration=10, economic_measurability=10, operational_maturity=10.

## What is authority custody?

Production signing key lifecycle management. Keys are generated via `openssl rand -hex 32`, stored in CI secrets (`DEEPSIGMA_SIGNING_KEY`), rotated every 90 days, and revoked via authority ledger entries. Each authority action now tracks `signing_key_id` for key provenance. See `docs/docs/security/KEY_CUSTODY.md`.

## What is the Reference Layer Manifesto?

The manifesto (`docs/manifesto.md`) defines three institutional failures that agentic AI creates — decision amnesia, authority vacuum, and silent drift — and the contract a reference layer must satisfy: intent explicit, authority verified, logic auditable, outcomes sealed.

## What is authority chain verification?

`verify_chain` walks the authority ledger and validates the SHA-256 hash chain linking every entry to its predecessor. If any entry has been tampered with, removed, or reordered, the chain breaks and verification fails. This makes the ledger tamper-evident. See `src/core/authority.py`.

## What is replay detection?

`detect_replay` fingerprints authority grant/revoke entries and detects duplicate submissions. This prevents replay attacks where an attacker resubmits a previously valid authority action. The fingerprint covers the action type, scope, principal, and timestamp.

## What is intent mutation detection?

Intent mutation detection compares the intent packet hash sealed into an episode against the hash at a later point (replay, audit, or subsequent run). If the hashes diverge, the intent was mutated after sealing — a governance violation. This catches unauthorized post-hoc changes to decision intent.

## What is the drift acceleration index?

A normalized 0–1 measure of how quickly KPI movements are accelerating across releases. Computed as the windowed average of second-derivative KPI deltas. Values > 0.80 indicate unsustainable release velocity. v2.1.0 value: 0.68 (WARN band, gate threshold is 0.50 for PASS).

## What is C-TEC?

Complexity-adjusted Time/Effort/Cost. C-TEC applies live governance health factors — ICR (Infrastructure Coherence Ratio) and PCR (PR Complexity Ratio) — to base TEC hours, producing three audience tiers: Internal ($1.64M), Executive ($2.47M), and Public Sector ($3.01M). v2.1.0 base hours: 10,963. Run via `make tec`.
