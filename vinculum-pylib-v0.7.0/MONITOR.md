> v0.7.0 retained core contract. See ARCHITECTURE.md and INPUT_RUNTIME_OUTPUT.md for the new pipeline.

# Pairing monitor

The monitor discovers candidates; the application selects; the hinge evaluates.

`PairingMonitor` receives normalized, versioned `Representation` events. It indexes candidates by entity and concept. Across L/M sides it checks supplied scope, population, denominator, granularity, location, definition version, unit dimension and exact time alignment. **Observed values never determine which pair is proposed.** Otherwise disagreement could prevent the very pairing needed to discover it.

## Output

`PairProposal` includes endpoint IDs, matched fields, pending fields, a metadata-completeness `match_score`, and an ambiguity flag. Match score is **not** a calibrated probability. Multiple candidate counterparts remain ambiguous; no strongest-looking value silently wins.

A proposal is not a hinge evaluation. `monitor.select(graph, proposal, rationale=...)` is an explicit application call. Selected pairs still pass all mandatory hinge checks. Selection does not create an inferred probability of one; alignment support remains unassessed unless an application supplies a justified coefficient separately.

## Runtime boundaries

This is a bounded in-memory reference monitor, not a background service, stream-processing cluster, Anduril connector or operational sensor integration. It rejects changed payloads reusing the same event ID; new revisions require new IDs. Buffer exhaustion raises an error rather than silently deleting old unresolved work. `expire_before(timestamp)` is explicit and returns evicted IDs. Missing-time/timeless records are not silently removed.

JSONL CLI:

```bash
vinculum-lattice monitor examples/monitor_events.jsonl
```

Persistence, live subscription, transport authentication, replay deduplication across processes, watermarks for out-of-order distributed streams and alert policy belong in an application adapter. The library does not operate any equipment or perform CERPA APPLY.
