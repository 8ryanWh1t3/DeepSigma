# Drift Schema — Drift Event

A **DriftEvent** is a structured signal emitted whenever the runtime detects a variance between expected and observed behaviour. Drift events are typed, fingerprinted, and linked to the episode that triggered them. They feed the Drift → Patch loop and contribute to the `DS` (Drift Scan) artifact in Coherence Ops.

**Schema file**: [`specs/drift.schema.json`](../specs/drift.schema.json)

---

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `driftId` | string | Stable unique ID for this drift signal. |
| `episodeId` | string | The episode that triggered the drift. |
| `driftType` | enum | Category of variance. See types below. |
| `severity` | enum | `green` / `yellow` / `red` |
| `detectedAt` | string (ISO-8601) | Timestamp of detection. |
| `evidenceRefs` | array of strings | IDs of the records, claims, or metrics that constitute evidence. |
| `recommendedPatchType` | enum | Suggested remediation. See patch types below. |
| `fingerprint` | object | Stable `{key, version}` hash for deduplication across episodes. |

---

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `notes` | string | Human-readable context or investigation notes. |

---

## Drift Types

| Type | Trigger | Typical Severity |
|------|---------|-----------------|
| `time` | Decision elapsed time exceeded `deadlineMs` | yellow / red |
| `freshness` | Context feature exceeded TTL at time of use (TOCTOU breach) | yellow / red |
| `fallback` | Degrade ladder step was invoked | green / yellow |
| `bypass` | Emergency bypass used (action dispatched without valid contract) | red |
| `verify` | Verifier returned `fail` or `inconclusive` | yellow / red |
| `outcome` | Post-action outcome differed from expected (anomaly) | yellow / red |
| `fanout` | Agent exceeded `maxFanout` or `maxHops` from DTE limits | yellow |
| `contention` | Resource lock or rate limit caused retry storm | yellow / red |

The Exhaust Inbox refiner adds two additional drift types used during episode refinement:

| Type | Trigger |
|------|---------|
| `contradiction` | Extracted claim contradicts existing canon |
| `stale_reference` | Memory item references an episode ID no longer in the graph |

---

## Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| `green` | Informational — within acceptable operating range | Log only |
| `yellow` | Warning — approaching threshold or single-event anomaly | Review within SLO window |
| `red` | Critical — threshold breached or safety violation | Immediate triage |

---

## Recommended Patch Types

| Patch Type | Description |
|-----------|-------------|
| `dte_change` | Adjust deadline, stage budget, or limit in the DTE |
| `ttl_change` | Increase or decrease TTL for a specific feature |
| `cache_bundle_change` | Update the cached context bundle used during degrade |
| `routing_change` | Redirect to a different model, tool, or data source |
| `verification_change` | Change verifier method or timeout |
| `action_scope_tighten` | Reduce blast radius or add preconditions to the action contract |
| `manual_review` | No automated patch — escalate to human review |

---

## Fingerprint

The `fingerprint.key` is a stable hash computed from `driftType + episodeId + evidence` that allows deduplication and trending across multiple episodes. Two drift events with the same fingerprint key are considered the same recurring pattern.

`fingerprint.version` identifies the hashing algorithm version so that fingerprints can be migrated when the algorithm changes.

---

## Relationship to Other Schemas

- **[DTE Schema](DTE-Schema)** — DTE parameters (deadlines, TTLs, limits) are the thresholds that drift measures against
- **[Episode Schema](Episode-Schema)** — drift events reference `episodeId` to trace back to the full decision context
- **[Action Contract Schema](Action-Contract-Schema)** — `bypass` drift fires when an action is dispatched without a valid contract
- **[Policy Pack Schema](Policy-Pack-Schema)** — `missing_policy` signals relate to policy pack stamp absence

---

## Coherence Ops Integration

Drift events feed the **DS (Drift Scan)** artifact in Coherence Ops. The `WHAT_DRIFTED` IRIS query aggregates drift events by fingerprint, severity, and resolution ratio. The patch workflow begins when a recurring fingerprint exceeds a configurable recurrence threshold.

---

## Related Pages

- [Drift → Patch](Drift-to-Patch) — full lifecycle from detection to remediation
- [Schemas](Schemas) — all JSON Schema specs
- [IRIS](IRIS) — `WHAT_DRIFTED` query type
- [Coherence Ops Mapping](Coherence-Ops-Mapping) — how drift feeds the DS artifact
- [Exhaust Inbox](Exhaust-Inbox) — drift detection during episode refinement
