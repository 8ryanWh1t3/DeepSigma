# Deep Sigma P2P C2 Python Library

Prototype library for **distributed command-and-control coherence**.

The design separates:

- **command intent / authority** — centrally defined and cryptographically referenceable
- **mission state** — replicated peer-to-peer
- **local reasoning** — each peer can operate while disconnected
- **reconciliation** — conflicting claims are preserved and surfaced rather than silently overwritten
- **memory** — every accepted or rejected change retains provenance and lineage

The package does **not** implement targeting, weapon control, autonomous engagement, or tactical radio drivers. Transport is abstracted behind an interface; the included transport is in-memory for tests and simulation.

## Core concepts

```text
Command Intent
    ↓
Authority Envelope
    ↓
Mission Object / DKO
    ↓
Peer Ledger
    ↓
Gossip / Delta Exchange
    ↓
Contradiction Detection
    ↓
CERPA-style Review / Patch / Apply
    ↓
Shared Coherent State
```

## Install

```bash
pip install -e .
```

## Quick start

```python
from deep_sigma_p2pc2 import (
    AuthorityEnvelope,
    MissionObject,
    PeerNode,
    Scope,
)

node_a = PeerNode("peer-a")
node_b = PeerNode("peer-b")

auth = AuthorityEnvelope(
    authority_id="cmd-001",
    issuer="HQ",
    subject="peer-a",
    scopes={Scope.OBSERVE, Scope.ASSESS},
)

node_a.install_authority(auth)

obj = MissionObject.observation(
    entity_id="entity-7",
    value="UNKNOWN",
    origin_peer="peer-a",
    confidence=0.64,
    authority_id="cmd-001",
)

node_a.publish(obj)
node_b.merge_delta(node_a.export_delta())

print(node_b.world.current("entity-7", "status"))
```

## Included modules

- `models.py` — mission objects, authority envelopes, claims, patches
- `authority.py` — bounded authority checks
- `ledger.py` — append-only event ledger
- `world.py` — local materialized mission/world model
- `reconcile.py` — contradiction detection and deterministic resolution candidates
- `peer.py` — peer runtime / sync API
- `storage.py` — SQLite persistence
- `transport.py` — transport protocol + in-memory simulation transport
- `cerpa.py` — Claim → Event → Review → Patch → Apply workflow
- `codec.py` — deterministic JSON serialization + hashing

## Design rule

> Centralize intent. Distribute understanding. Delegate authority. Replicate memory. Reconcile truth.
