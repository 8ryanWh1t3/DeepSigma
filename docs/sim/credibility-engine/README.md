---
title: "Credibility Engine Simulation"
version: "1.0.0"
status: "Stage 2"
last_updated: "2026-02-19"
---

# Credibility Engine — Stage 2 Simulation

A time-driven simulation harness that powers the [Credibility Engine Demo Cockpit](../../dashboard/credibility-engine-demo/) with live synthetic data.

---

## What This Is

Stage 2 converts the static demo dashboard into a live simulation. The runner advances the engine every 2 seconds, producing drift events, compressing quorum margins, increasing correlation coefficients, decaying TTL windows, and degrading sync plane integrity. The dashboard auto-refreshes to reflect the changing state.

This is **not** a production engine. It is a simulation of institutional-scale truth maintenance dynamics.

---

## How to Run

**Terminal 1 — Start the simulation:**

```bash
python sim/credibility-engine/runner.py --scenario day0
```

**Terminal 2 — Serve the dashboard:**

```bash
python -m http.server 8000
```

Then visit: [http://localhost:8000/dashboard/credibility-engine-demo/](http://localhost:8000/dashboard/credibility-engine-demo/)

The dashboard will update every 2 seconds as the simulation writes new JSON snapshots.

---

## Scenarios

| Scenario | Description | Index Range | Key Events |
|----------|-------------|-------------|------------|
| `day0` | Baseline — stable lattice | 94–97 | Minimal drift, healthy quorum, low correlation |
| `day1` | Entropy emerges | 85–90 | Drift increases, CG-002 crosses REVIEW, quorum compresses |
| `day2` | Coordinated darkness | 65–75 | Silent nodes, Tier 0 flips UNKNOWN, sync watermark lag |
| `day3` | External mismatch + recovery | 45–60 then partial recovery | CRITICAL correlation, replay flags, patch-driven recovery |

### Switch scenarios:

```bash
# Run with a specific scenario
python sim/credibility-engine/runner.py --scenario day2

# Or hot-swap during runtime by creating scenario.json in the dashboard dir:
echo '{"scenario": "day3"}' > dashboard/credibility-engine-demo/scenario.json
```

---

## Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--scenario` | `day0` | Scenario to run: `day0`, `day1`, `day2`, `day3` |
| `--interval` | `2` | Seconds between ticks |
| `--output-dir` | `dashboard/credibility-engine-demo/` | Where to write JSON snapshots |

---

## Architecture

```
sim/credibility-engine/
├── runner.py      — CLI entrypoint, tick loop, atomic file writes
├── engine.py      — Simulation engine: state management, tick logic, JSON export
├── models.py      — Data models: Claim, CorrelationCluster, SyncRegion, DriftFingerprint
├── scenarios.py   — Day0–Day3 scenario phase definitions
├── packet.py      — Credibility Packet generator (DLR/RS/DS/MG + seal)
└── README.md      — This file
```

### Tick Lifecycle

Each tick (2 real seconds = 15 simulated minutes):

1. Decrement TTL remaining on all claims
2. Inject drift events (rate + severity from scenario phase)
3. Adjust correlation coefficients toward phase targets
4. Apply claim effects (margin compression, status changes)
5. Update sync plane metrics (skew, lag, replays)
6. Recalculate Credibility Index (6 components)
7. Generate Credibility Packet (DLR + RS + DS + MG + seal)
8. Write all 7 JSON files atomically

### Index Calculation

```
Index = base(60) + integrity + drift_penalty + correlation_penalty
        + quorum_penalty + ttl_penalty + confirmation_bonus
```

Clamped to 0–100.

### Atomic Writes

All JSON files are written atomically: write to temp file, then `os.replace()` to target. This prevents the dashboard from reading partial files.

---

## Output Files

Written to `dashboard/credibility-engine-demo/` each tick:

| File | Content |
|------|---------|
| `credibility_snapshot.json` | Index score, band, trend, 6 components |
| `claims_tier0.json` | 5 Tier 0 claims with quorum and TTL |
| `drift_events_24h.json` | Accumulated events, severity, categories, fingerprints |
| `correlation_map.json` | 6 clusters with live coefficients |
| `ttl_timeline.json` | 4-hour expiration forecast |
| `sync_integrity.json` | 3 regions + federation health |
| `credibility_packet_example.json` | Sealed DLR/RS/DS/MG assessment |

---

## Guardrails

- Abstract institutional credibility architecture only
- No real-world weapon modeling
- No operational defense content
- No external API dependencies
- Fully local simulation
- All data is synthetic

---

## Related

- [Credibility Engine Docs](../../docs/credibility-engine/)
- [Demo Cockpit](../../dashboard/credibility-engine-demo/)
- [Credibility Index Specification](../../docs/credibility-engine/credibility_index.md)
- [Lattice Architecture Diagram](../../mermaid/38-lattice-architecture.md)
