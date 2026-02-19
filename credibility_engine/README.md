---
title: "Credibility Engine — Runtime Module"
version: "0.7.0"
status: "Stage 3"
last_updated: "2026-02-19"
---

# Credibility Engine — Stage 3 Runtime

A real runtime Credibility Engine with JSONL persistence and API endpoints, replacing the simulation-only Stage 2 architecture.

---

## What This Is

Stage 3 converts the simulated engine into a real runtime module. The engine maintains live claim state, persists drift events, calculates the Credibility Index, writes canonical artifacts, and exposes FastAPI endpoints. The Stage 2 simulator can optionally drive the engine as an input source.

This is **not** a production engine. It is an abstract institutional credibility architecture.

---

## Architecture

```
credibility_engine/
├── __init__.py    — Module exports
├── engine.py      — CredibilityEngine: state management, index recalculation
├── models.py      — Data models: Claim, DriftEvent, CorrelationCluster, SyncRegion, Snapshot
├── store.py       — JSONL persistence: append-only storage for all entity types
├── index.py       — Credibility Index calculation (0-100, 5 bands, 5 penalties)
├── packet.py      — Credibility Packet generator (DLR/RS/DS/MG + seal)
├── api.py         — FastAPI router with 6 endpoints
└── README.md      — This file
```

---

## How to Run

**Start the API server:**

```bash
uvicorn dashboard.api_server:app --reload
```

**API endpoints:**

| Endpoint | Description |
|----------|-------------|
| `GET /api/credibility/snapshot` | Credibility Index, band, components, trend |
| `GET /api/credibility/claims/tier0` | 5 Tier 0 claims with quorum and TTL |
| `GET /api/credibility/drift/24h` | Drift events by severity, category, region |
| `GET /api/credibility/correlation` | 6 correlation clusters with coefficients |
| `GET /api/credibility/sync` | 3 sync regions + federation health |
| `GET /api/credibility/packet` | Sealed credibility packet (DLR/RS/DS/MG) |

---

## Persistence

Engine state persists to `data/credibility/` as JSONL files:

| File | Content |
|------|---------|
| `claims.jsonl` | Tier 0 claim state snapshots |
| `drift.jsonl` | Drift events (append-only) |
| `snapshots.jsonl` | Credibility Index snapshots |
| `correlation.jsonl` | Correlation cluster state |
| `sync.jsonl` | Sync region state |
| `packet_latest.json` | Latest sealed credibility packet |

---

## Dashboard Integration

The dashboard supports two data modes:

| Mode | Source | Config |
|------|--------|--------|
| `MOCK` | Local JSON files (default) | `DATA_MODE = "MOCK"` |
| `API` | Runtime engine API | `DATA_MODE = "API"` |

Toggle in `dashboard/credibility-engine-demo/app.js` (line 4).

---

## Simulation Integration

The Stage 2 simulator can drive the runtime engine:

```bash
python sim/credibility-engine/runner.py --scenario day1 --mode engine
```

When in engine mode, the simulator calls `engine.process_drift_event()` and
`engine.update_claim_state()` instead of writing JSON files directly.

---

## Guardrails

- Abstract institutional credibility architecture only
- No real-world weapon modeling
- No operational defense content
- No external API dependencies
- All data is synthetic

---

## Related

- [Credibility Engine Docs](../docs/credibility-engine/)
- [Demo Cockpit](../dashboard/credibility-engine-demo/)
- [Stage 2 Simulation](../sim/credibility-engine/)
