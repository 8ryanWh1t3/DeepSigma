# Event Contracts — Routing Table & Function Declarations

> Every function has a contract. Every event has a declaration. The routing table is the single source of truth.

## Overview

Event Contracts define the declarative routing table that maps all 36 domain function handlers and 39 events to their FEEDS topics, subtypes, handler paths, required payload fields, and emitted events.

**Modules**:
- `src/core/feeds/contracts/routing_table.json` — the manifest
- `src/core/feeds/contracts/loader.py` — load, query, fingerprint
- `src/core/feeds/contracts/validator.py` — publish-time validation

**Schemas**:
- `src/core/schemas/feeds/event_contract.schema.json` — per-function contract schema
- `src/core/schemas/feeds/routing_table.schema.json` — routing manifest schema

## Function Contract Format

Each function entry in the routing table:

```json
{
  "INTEL-F01": {
    "name": "claim_ingest",
    "domain": "intelops",
    "description": "Ingest a new claim into the truth layer via FEEDS.",
    "inputTopic": "truth_snapshot",
    "inputSubtype": "claim_ingest",
    "outputTopics": ["canon_entry", "drift_signal"],
    "outputSubtypes": ["claim_accepted", "claim_rejected"],
    "handler": "core.modes.intelops.claim_ingest",
    "requiredPayloadFields": ["claimId", "statement", "confidence"],
    "emitsEvents": ["INTEL-E01", "INTEL-E02"],
    "stateWrites": ["canon_store", "memory_graph"],
    "preconditions": ["claim has valid claimId"],
    "postconditions": ["claim persisted in canon store"]
  }
}
```

## Function Registry (36 Functions)

### IntelOps (12)

| ID | Name | Input Topic | Input Subtype |
|----|------|-------------|---------------|
| INTEL-F01 | `claim_ingest` | truth_snapshot | claim_ingest |
| INTEL-F02 | `claim_validate` | canon_entry | claim_accepted |
| INTEL-F03 | `claim_drift_detect` | drift_signal | claim_contradiction |
| INTEL-F04 | `claim_patch_recommend` | drift_signal | claim_drift |
| INTEL-F05 | `claim_mg_update` | canon_entry | patch_recommended |
| INTEL-F06 | `claim_canon_promote` | canon_entry | claim_accepted |
| INTEL-F07 | `claim_authority_check` | decision_lineage | authority_check |
| INTEL-F08 | `claim_evidence_verify` | decision_lineage | evidence_check |
| INTEL-F09 | `claim_triage` | drift_signal | claim_drift |
| INTEL-F10 | `claim_supersede` | canon_entry | retcon_executed |
| INTEL-F11 | `claim_half_life_check` | drift_signal | half_life_sweep |
| INTEL-F12 | `claim_confidence_recalc` | drift_signal | confidence_decay |

### FranOps (12)

| ID | Name | Input Topic | Input Subtype |
|----|------|-------------|---------------|
| FRAN-F01 | `canon_propose` | canon_entry | canon_proposed |
| FRAN-F02 | `canon_bless` | canon_entry | canon_proposed |
| FRAN-F03 | `canon_enforce` | canon_entry | canon_blessed |
| FRAN-F04 | `retcon_assess` | canon_entry | retcon_request |
| FRAN-F05 | `retcon_execute` | canon_entry | retcon_assessed |
| FRAN-F06 | `retcon_propagate` | canon_entry | retcon_executed |
| FRAN-F07 | `inflation_monitor` | drift_signal | canon_inflation |
| FRAN-F08 | `canon_expire` | canon_entry | canon_expire_sweep |
| FRAN-F09 | `canon_supersede` | canon_entry | claim_superseded |
| FRAN-F10 | `canon_scope_check` | canon_entry | scope_check |
| FRAN-F11 | `canon_drift_detect` | drift_signal | canon_drift |
| FRAN-F12 | `canon_rollback` | canon_entry | canon_rollback |

### ReflectionOps (12)

| ID | Name | Input Topic | Input Subtype |
|----|------|-------------|---------------|
| RE-F01 | `episode_begin` | decision_lineage | episode_begin |
| RE-F02 | `episode_seal` | decision_lineage | episode_active |
| RE-F03 | `episode_archive` | decision_lineage | episode_sealed |
| RE-F04 | `gate_evaluate` | drift_signal | gate_request |
| RE-F05 | `gate_degrade` | drift_signal | gate_deny |
| RE-F06 | `gate_killswitch` | drift_signal | killswitch_request |
| RE-F07 | `audit_non_coercion` | decision_lineage | episode_active |
| RE-F08 | `severity_score` | drift_signal | severity_request |
| RE-F09 | `coherence_check` | drift_signal | coherence_request |
| RE-F10 | `reflection_ingest` | decision_lineage | episode_sealed |
| RE-F11 | `iris_resolve` | decision_lineage | iris_query |
| RE-F12 | `episode_replay` | decision_lineage | episode_replay |

## Querying the Routing Table

```python
from core.feeds.contracts.loader import load_routing_table

rt = load_routing_table()

# Look up a function
fn = rt.get_function("INTEL-F01")
print(fn.handler)  # "core.modes.intelops.claim_ingest"

# Look up an event
ev = rt.get_event("INTEL-E01")
print(ev.produced_by)  # ("INTEL-F01",)

# Get handler path
path = rt.get_handler("FRAN-F04")

# Get consumers of an event
consumers = rt.get_consumers("INTEL-E06")

# Get all functions in a domain
fns = rt.functions_by_domain("intelops")

# Get functions for a topic/subtype
fns = rt.functions_for_topic("drift_signal", "claim_contradiction")
```

## Contract Validation

At publish time, the validator checks:
1. Event has required payload fields per contract
2. Output topics and subtypes match declared outputs
3. State writes are consistent with handler declaration

**Implementation**: `src/core/feeds/contracts/validator.py`

## Fingerprinting

The routing table has a SHA-256 fingerprint computed over the `functions` and `events` sections (sorted keys, compact JSON). This fingerprint is embedded in the manifest and verified by CI.

## FEEDS Topic Mapping

All 36 functions route through the existing 6 FEEDS topics:

| Topic | Functions |
|-------|-----------|
| `truth_snapshot` | INTEL-F01 |
| `canon_entry` | INTEL-F02, F05, F06, F10; FRAN-F01–F06, F08–F10, F12 |
| `drift_signal` | INTEL-F03, F04, F07–F09, F11, F12; FRAN-F07, F11; RE-F04–F06, F08, F09 |
| `decision_lineage` | INTEL-F07, F08; RE-F01–F03, F07, F10–F12 |
| `mg_update` | INTEL-F05 |
| `coherence_report` | RE-F09 |

## Related Pages

- [IntelOps](IntelOps) — claim lifecycle domain
- [FranOps](FranOps) — canon enforcement domain
- [ReflectionOps](ReflectionOps) — gate enforcement domain
- [Cascade Engine](Cascade-Engine) — cross-domain propagation
- [FEEDS Pipeline](FEEDS-Pipeline) — event-driven pub/sub
