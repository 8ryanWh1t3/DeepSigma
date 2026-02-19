---
title: "Credibility Engine Demo Cockpit"
version: "1.0.0"
status: "Demo"
last_updated: "2026-02-19"
---

# Credibility Engine — Demo Cockpit

A static demonstration of the Credibility Engine cockpit surface. Institutional-scale truth maintenance visible in under 30 seconds.

---

## What This Is

A self-contained, static dashboard that renders the Credibility Engine's operational state from mock JSON data. No backend. No database. No API. Just HTML, CSS, JS, and seven data files.

This is a cockpit surface — not a product fork, not a monitoring tool.

---

## What It Shows

| Panel | What It Displays |
|-------|-----------------|
| **Credibility Index** | Composite 0–100 score, trend, 6 component breakdown, interpretation bands |
| **Tier 0 Claims** | Foundational claims with status, quorum (K/N), margin, TTL, correlation groups, out-of-band |
| **Drift Activity (24h)** | 183 events by severity, 5 institutional categories, top fingerprints |
| **Correlation Risk** | 6 clusters with coefficients — green (<0.7), yellow (0.7–0.9), red (>0.9) |
| **TTL Expiration Timeline** | Upcoming expirations by tier, clustering warnings, Tier 0 alerts |
| **Sync Plane Integrity** | 3 regions — time skew, watermark lag, beacon health, federation status |
| **Credibility Packet** | Generate sealed assessment (DLR + RS + DS + MG summary) |

---

## How to Run

Open `index.html` directly in a browser:

```bash
open index.html
```

Or serve locally:

```bash
cd dashboard/credibility-engine-demo
python -m http.server 8000
```

Then visit: [http://localhost:8000](http://localhost:8000)

---

## File Inventory

| File | Purpose |
|------|---------|
| `index.html` | Dashboard layout (7 panels) |
| `styles.css` | Institutional cockpit theme |
| `app.js` | Fetch JSON, render panels, packet export |
| `credibility_snapshot.json` | Index score, trend, components, bands |
| `claims_tier0.json` | 5 Tier 0 claims with quorum and TTL |
| `drift_events_24h.json` | 183 events, 5 categories, top fingerprints |
| `correlation_map.json` | 6 correlation clusters with coefficients |
| `ttl_timeline.json` | 4-hour expiration forecast with clustering |
| `sync_integrity.json` | 3 regions + federation health |
| `credibility_packet_example.json` | Sealed DLR/RS/DS/MG assessment packet |

---

## Scale Calibration

All mock data is calibrated to the [Credibility Engine at Scale](../../examples/03-credibility-engine-scale/) example:

- 36,000 active nodes across 3 regions
- Credibility Index: 92 (Minor Drift band)
- 183 drift events in 24h (within 100–400 steady state)
- 1 Tier 0 claim in UNKNOWN state (quorum broken)
- 1 correlation cluster at 0.91 (CRITICAL)
- TTL clustering detected (68 nodes in 15-minute window)

---

## Guardrails

This demo uses mock data and models no real-world system. Abstract institutional credibility architecture only. No domain-specific content. No weapon modeling. No operational details.

---

## Related Documentation

- [Credibility Engine docs](../../docs/credibility-engine/)
- [Credibility Index specification](../../docs/credibility-engine/credibility_index.md)
- [Core System Design](../../docs/credibility-engine/core_system_design.md)
- [Sync Plane](../../docs/credibility-engine/sync_plane.md)
- [Lattice Architecture diagram](../../mermaid/38-lattice-architecture.md)
- [Drift Loop diagram](../../mermaid/39-drift-loop.md)
