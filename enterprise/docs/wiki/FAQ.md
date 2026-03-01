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

## What is the RuntimeGate?

A composable pre-execution policy constraint evaluator. Operators define gate rules in their policy pack (`"gates"` array); the RuntimeGate evaluates all constraints before execution and returns allow/deny/degrade with a machine-readable rationale. Five gate types: freshness, verification, latency_slo, quota, and custom expression. Generalizes the degrade ladder's hard gates into a pluggable system. See `src/engine/runtime_gate.py`.

## What is the SLO circuit breaker?

A metric-level safety mechanism that trips when a monitored value (e.g., P99 latency) exceeds a threshold for a sustained time window. When tripped, the RuntimeGate automatically degrades or denies execution. Resets when the metric returns to normal. Configured per gate rule in the policy pack.

## How does connector auto-instrumentation work?

The `@traced` decorator wraps any adapter method in an OTel span with connector name, operation, duration, and status attributes. The `InstrumentedConnector` mixin auto-wraps all public methods on subclass initialization. W3C `traceparent` inject/extract helpers propagate trace context across HTTP calls. See `src/adapters/otel/instrumentation.py`.

## How does tool-call span tracing work?

The OTel exporter now has `export_tool_call()` and `export_llm_call()` methods. Each produces a child span with tool/model-specific attributes (tool_name, tool_version, status, duration_ms for tools; model, prompt_tokens, completion_tokens, total_tokens, latency_ms for LLM calls). Three new histograms: `sigma.tool.latency_ms`, `sigma.llm.latency_ms`, `sigma.llm.tokens.total`.

## How does encryption-at-rest work?

`FileEncryptor` uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` package. Key sourced from `DEEPSIGMA_ENCRYPTION_KEY` env var or `DEEPSIGMA_ENCRYPTION_KEY_FILE`. The compliance export CLI accepts `--encrypt` to encrypt all output artifacts and `--schedule N` for cron-friendly auto-export of the last N days. See `src/governance/encryption.py`.

## How does fairness monitoring work?

DeepSigma uses a hybrid approach: external fairness tools (AIF360, Fairlearn, or custom pipelines) compute fairness metrics, and DeepSigma ingests their reports as drift signals. Three new drift types: `demographic_parity_violation`, `disparate_impact`, `fairness_metric_degradation`. The `ingest_fairness_report()` function converts external JSON reports to DriftSignal objects. Convenience wrappers exist for AIF360 and Fairlearn output. See `src/adapters/fairness/ingest.py`.

## What are domain modes?

Three executable domain mode modules that wire existing building blocks (FEEDS, Memory Graph, claim validator, canon store, drift detection) into automated pipelines with deterministic replay:

- **IntelOps** — 12 function handlers (INTEL-F01–F12) for claim lifecycle automation: ingest, validate, drift detect, patch recommend, MG update, canon promote, authority check, evidence verify, triage, supersede, half-life check, confidence recalc.
- **FranOps** — 12 function handlers (FRAN-F01–F12) for canon enforcement: propose, bless, enforce, retcon assess/execute/propagate, inflation monitor, expire, supersede, scope check, drift detect, rollback.
- **ReflectionOps** — 12 function handlers (RE-F01–F12) for gate enforcement: episode begin/seal/archive, gate evaluate/degrade/killswitch, non-coercion audit, severity score, coherence check, reflection ingest, IRIS resolve, episode replay.

Every handler returns a `FunctionResult` with `replay_hash` (SHA-256) for deterministic verification. See `src/core/modes/`.

## What is the cascade engine?

Cross-domain event propagation with 7 declarative rules. When an event in one domain matches a rule, the cascade engine invokes the target domain's handler. Rules include: claim contradiction → canon review, canon retcon → episode flag, killswitch → all domains freeze. Depth-limited to prevent infinite loops. See `src/core/modes/cascade.py`.

## What are event contracts?

A declarative routing table (`src/core/feeds/contracts/routing_table.json`) mapping all 36 function handlers + 39 events to their FEEDS topics, subtypes, handler paths, required payload fields, and emitted events. Contract validation occurs at publish time. Query the table via `RoutingTable.get_function()` and `get_event()`.

## What is the canon workflow state machine?

Canon entries have a lifecycle: PROPOSED → BLESSED → ACTIVE → UNDER_REVIEW → SUPERSEDED/RETCONNED/EXPIRED. Also supports REJECTED and FROZEN states. Transition validation prevents illegal state changes (e.g., EXPIRED cannot return to ACTIVE). See `src/core/feeds/canon/workflow.py`.

## What is the episode state machine?

Episodes have a lifecycle: PENDING → ACTIVE → SEALED → ARCHIVED. The FROZEN state supports killswitch scenarios. `freeze_all()` halts all active episodes. See `src/core/episode_state.py`.

## What is the non-coercion audit log?

An append-only, hash-chained NDJSON log for domain mode actions. Each entry chains to the previous via SHA-256 hash, making the log tamper-evident. `verify_chain()` validates integrity. Used by ReflectionOps RE-F07 for non-coercion attestation. See `src/core/audit_log.py`.

## What is the domain killswitch?

An emergency halt mechanism: freezes all ACTIVE episodes, emits a sealed halt proof with authorization details, logs to the audit trail, and emits a drift signal on all FEEDS topics. Requires explicit authority check to resume. See `src/core/killswitch.py`.

## What is the Money Demo v2?

A 10-step end-to-end pipeline exercising all 3 domain modes: LOAD → INTELOPS INGEST → VALIDATE → DELTA → FRANOPS PROPOSE → RETCON → REOPS EPISODE → CASCADE → COHERENCE → SEAL. Uses fixture data (3 baseline claims + 1 contradiction) to demonstrate drift detection, retcon execution, cascade propagation, and coherence scoring. Run via `make demo-money` or `python -m demos.money_demo`.

## What is JRM?

The Judgment Refinement Module — a log-agnostic coherence engine that ingests external telemetry (Suricata EVE, Snort fast.log, Copilot agent logs), normalizes events via format-specific adapters, runs a 5-stage coherence pipeline (Truth → Reasoning → Drift → Patch → Memory Graph), and outputs standardized JRM-X packet zips. JRM is independent from FEEDS but reuses the same hashing conventions (`sha256:<hex>`) and memory graph primitives. See `src/core/jrm/`.

## What log formats does JRM support?

Three built-in adapters:

| Adapter | Format | Event Types |
| --- | --- | --- |
| `suricata_eve` | Suricata EVE JSON lines | alert, dns, http, flow, tls, fileinfo |
| `snort_fastlog` | Snort fast.log `[GID:SID:REV]` | alerts with priority mapping |
| `copilot_agent` | Copilot/agent JSONL | prompt, tool_call, response, guardrail |

All adapters are lossless — malformed lines become `MALFORMED` event type with raw bytes preserved. New adapters plug in via `register_adapter()`.

## What is a JRM-X packet?

A zip file containing 6 canonical data files + manifest: truth_snapshot.json, authority_slice.json, decision_lineage.jsonl, drift_signal.jsonl, memory_graph.json, canon_entry.json, and manifest.json (SHA-256 per file). The rolling packet builder auto-flushes at 50k events or 25MB zip size. Naming convention: `JRM_X_PACKET_<ENV>_<start>_<end>_partNN`.

## What drift does JRM detect locally?

Four local drift types:

- **FP_SPIKE** — same signature fires many times with low confidence (false positive burst)
- **MISSING_MAPPING** — events with no corresponding claim in the truth layer
- **STALE_LOGIC** — conflicting signature revisions across events in the same window
- **ASSUMPTION_EXPIRED** — assumptions past their half-life TTL

## What is JRM federation?

Enterprise-only cross-environment coherence. The JRM Hub ingests packets from multiple SOC environments and detects cross-env drift:

- **VERSION_SKEW** — same signature_id has different active revisions across environments
- **POSTURE_DIVERGENCE** — same signature_id has confidence delta >0.3 across environments

The Gate validates packet integrity and enforces environment scope. The Advisory Engine publishes drift advisories that operators can accept or decline. Packets are signed with HMAC-SHA256.

## How do I run JRM?

```bash
# Normalize Suricata logs
coherence jrm ingest --adapter suricata_eve --in eve.json --out normalized.ndjson

# Run pipeline and produce packets
coherence jrm run --in normalized.ndjson --env SOC_EAST --packet-out /tmp/packets/

# Validate a packet
coherence jrm validate /tmp/packets/*.zip

# List available adapters
coherence jrm adapters
```

Enterprise federation commands are available via the `deepsigma` CLI: `jrm federate`, `jrm gate validate`, `jrm hub replay`, `jrm advisory publish`.

## What is JRM EDGE?

A standalone single-file HTML app (`edge/EDGE_JRM_EDGE_v1.0.7.html`) that runs the JRM pipeline in the browser. Load Suricata, Snort, or Copilot logs, run a seeded 9-stage pipeline, and explore events, packets, health metrics, and drift — all offline, zero dependencies. Current version: v1.0.7.

## What did JRM EDGE v1.0.7 add?

Five features: (1) **So What panel** — per-stage what/why/next analysis auto-generated from pipeline metrics, (2) **Analyzer vs Deep Sigma view** — toggle between SOC terminology and governance terminology, (3) **Packet chain timeline + diff** — horizontal bar showing packet parts with inter-packet diff computation, (4) **Stream mode + Freeze & Seal** — simulated `tail -f` with rolling window, freeze pauses view, seal captures snapshot, (5) **Policy drawer** — locked-by-default editable thresholds with regression rerun and delta comparison.

## What is the EDGE Policy Drawer?

A guarded panel in JRM EDGE (v1.0.7+) exposing 8 pipeline thresholds: FP spike count/confidence, stale rev count, confidence review/patch thresholds, severity multiplier, confidence floor/ceil. Locked by default — unlock requires confirmation. After editing, "Regression Rerun" re-executes the full test suite and shows delta vs the baseline snapshot.

## What is the RFP Co-Pilot?

An EDGE module (`edge/edge_rfp_copilot_excel_json.html`) for government RFP extraction. One person runs a structured AI prompt against the RFP document, producing a JSON file. Excel Power Query loads the JSON into 6 live tables (Solicitation, Key Dates, Attachments, Amendments, Risks, Open Items). Each proposal role pulls what they need from the shared JSON. Amendments? Rerun the prompt, overwrite the JSON, Refresh All in Excel. A 1-page executive brief is also available (`edge/edge_rfp_copilot_exec_brief.html`).

## How does the RFP Co-Pilot refresh loop work?

Amendment arrives → rerun the extraction prompt with the updated RFP → overwrite `rfp_extract.json` → Ctrl+Alt+F5 (Refresh All) in Excel → all 6 tables update automatically → team stays aligned. No one re-reads the full RFP.

## What is Domino Delegation Encryption?

A 4-of-7 Shamir threshold encryption ceremony using physical domino tiles as co-presence proof. Seven participants each draw a domino tile, chain them together, generate Shamir keyword shares, and can encrypt/decrypt sensitive text via AES-256-GCM. Keywords are TTL-gated (1 hour) and distributed one at a time in person only. Enterprise edition: `enterprise/edge/EDGE_Domino_Delegation_Encryption.html`. Core verifier: `core/edge/EDGE_Domino_Delegation_Encryption_Verifier.html`.

## How does the Domino ceremony work?

Seven participants each draw a physical domino tile from a double-six set. They enter tiles into the EDGE module in order, validating that the right side of each tile matches the left side of the next (standard domino chaining). The tool computes a SHA-256 seal of the chain, generates 7 Shamir shares (4-of-7 threshold), and assigns each participant one keyword (base64 Shamir share). The ceremony JSON (public record) captures chain fingerprint, participant list, keyword fingerprints, and TTL window. It never includes the keywords or secret.

## What is public vs secret in a Domino ceremony?

**Public (ceremony JSON):** chain string, chain seal (SHA-256), chain fingerprint (quick ID), domino name, participant list, session ID, keyword fingerprints, TTL window. Safe to store, share, and archive. **Secret (never recorded):** the 7 keywords (Shamir shares), the reconstructed secret, the passphrase, and any plaintext. Distribute keywords in person only; never transmit electronically.

## What happens when Domino keywords expire?

Keywords are valid for 1 hour from generation. After TTL expires, the tool revokes the unlock and keywords cannot reconstruct the secret. A new ceremony must be conducted to generate fresh keywords. This enforces ceremony freshness and prevents long-term keyword accumulation.

## What is the Domino Delegation Verifier?

A read-only EDGE tool (`core/edge/EDGE_Domino_Delegation_Encryption_Verifier.html`) that loads a ceremony JSON and verifies: chain connectivity, chain seal recomputation (SHA-256), TTL status (active/expired), session ID, and keyword fingerprints. It cannot generate keywords, accept keywords, or encrypt/decrypt. Useful for independent audit of ceremony records.
