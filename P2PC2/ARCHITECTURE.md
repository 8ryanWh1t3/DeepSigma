# Architecture

## Principle

**Peer-to-peer C2 is not peer-to-peer authority.**

The library keeps command authority explicit while allowing peers to retain local state, operate disconnected, exchange deltas, and reconcile after reconnection.

## Layers

1. **Authority** — immutable authority envelopes and scope evaluation
2. **Mission objects** — small, versioned semantic objects carrying provenance
3. **Ledger** — append-only local event history
4. **World model** — current local projection over retained historical assertions
5. **Transport** — pluggable delivery interface
6. **Reconciliation** — contradiction discovery and deterministic candidate ranking
7. **CERPA** — governed Claim → Event → Review → Patch → Apply closure
8. **Persistence** — SQLite local store for disconnected operation

## Safety / control boundary

The library deliberately omits:

- weapon-control interfaces
- target selection
- fire-control logic
- autonomous engagement
- radio waveform implementation
- classified network assumptions

Those concerns remain outside the package and should be governed by their own accredited systems and human authority.
