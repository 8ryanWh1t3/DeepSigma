<p align="center">
  <img src="docs/assets/overwatch-logo.svg" alt="Σ OVERWATCH" width="160" />
</p>




<h1 align="center">Σ OVERWATCH</h1>




<p align="center"><b>The control plane for agentic AI:</b> deadlines • freshness • safe actions • verification • sealed episodes</p>




<p align="center">
  <img src="https://img.shields.io/badge/AL6-Governed-blue" />
  <img src="https://img.shields.io/badge/DTE-Enforced-blue" />
  <img src="https://img.shields.io/badge/TTL-Freshness%20Gates-blue" />
  <img src="https://img.shields.io/badge/Safe%20Actions-Contracts-blue" />
  <img src="https://img.shields.io/badge/Outcomes-Verified-blue" />
  <img src="https://img.shields.io/badge/Episodes-Sealed-blue" />
  <img src="https://img.shields.io/badge/Drift-Patch-blue" />
</p>




---




## What is Σ OVERWATCH?
**Σ OVERWATCH makes agentic automation production-safe.**  
It wraps any agent stack and enforces **Decision Timing Envelopes (DTE)**: deadlines, stage budgets, TTL freshness gates, degrade ladders, safe action contracts (idempotency/rollback), mandatory verification, and **sealed DecisionEpisodes** for audit and drift→patch learning.




> We don’t sell agents. We sell the ability to trust agents.




## Why it exists
Agentic AI is hot. Production success is not.  
Most failures aren’t “model errors” — they’re **late decisions**, **stale context**, **tail-latency spikes**, and **unsafe actions** shipped without rollback + verification.




## The simple model (AL6)
Agentic reliability is 6 dimensions:
1) **Deadline** (decision window ms)
2) **Distance** (hops/fan-out)
3) **Data Freshness** (TTL/snapshot age)
4) **Variability** (P95/P99 + jitter)
5) **Drag** (queue/lock/IO contention)
6) **Degrade** (fallback/bypass/abstain)




## Contracts
- **DTE** (`/specs/dte.schema.json`) — deadlines + budgets + TTL + degrade ladder  
- **Action Contract** (`/specs/action_contract.schema.json`) — blast radius + idempotency + rollback + auth mode  
- **DecisionEpisode** (`/specs/episode.schema.json`) — sealed truth→reasoning→action→verify→outcome  
- **Drift** (`/specs/drift.schema.json`) — time/freshness/fallback/bypass/verify/outcome drift → patch hints  




## Quickstart
See `/examples/demo-stack/` for a 3-minute demo (scaffolded):
- ✅ meets deadline + TTL → act → verify → seal
- ❌ stale feature → degrade → abstain → drift
- ❌ tool spike → circuit breaker → fallback → drift
- ❌ unsafe action → blocked (no idempotency/rollback) → drift


## Dashboard


Interactive monitoring dashboard with real-time visualizations. **Zero-install demo** — just open in your browser:


➡ [`dashboard/demo.html`](./dashboard/demo.html)


Features: dark/light theme, system health gauge, radar charts, searchable tables, keyboard shortcuts (`1-4` views, `R` refresh, `T` theme), toast alerts, JSON/CSV export.


Full React build version: see [`/dashboard`](./dashboard/) with `npm install && npm run dev`.


## OpenClaw integration (scaffold)
See `/adapters/openclaw/` for the planned adapter: **Skill Runner → Action Contract → Verify → Seal**.








## MCP transport (scaffold)
See `/adapters/mcp/` for a minimal MCP JSON-RPC stdio server scaffold exposing Overwatch primitives as MCP tools.








## Coherence Ops integration
See `docs/10-coherence-ops-integration.md` for how RAL/Σ OVERWATCH maps to DLR/RS/DS/MG and the LLM Data Model.





## New in vNext (Scaffold Features)
- **Policy Packs**: versioned enforcement bundles (`/policy_packs/`)
- **Degrade Ladder Engine**: executable degrade selection (`/engine/degrade_ladder.py`)
- **Verifier library**: read-after-write + invariants (`/verifiers/`)
- **Replay harness**: deterministic replay scaffolding (`/tools/replay_episode.py`)
- **OpenTelemetry hooks**: exporter placeholder (`/adapters/otel/`)

Docs:
- `docs/11-policy-packs.md`
- `docs/12-degrade-ladder.md`
- `docs/13-verifiers.md`
- `docs/14-replay.md`
- `docs/15-otel.md`


### Policy stamping (vNext)
Sealed episodes now record `policyPackId/version/hash` and the chosen `degrade.step` + rationale.


## 60-second demo (one command)
```bash
# Ensure project root is on PYTHONPATH
PYTHONPATH=. python tools/run_supervised.py \
  --decisionType AccountQuarantine \
  --policy policy_packs/packs/demo_policy_pack_v1.json \
  --telemetry endToEndMs=95 p99Ms=160 jitterMs=70 \
  --context ttlBreachesCount=0 maxFeatureAgeMs=180 \
  --verification pass \
  --out episodes_out
```
See `docs/16-run-supervised.md`.
