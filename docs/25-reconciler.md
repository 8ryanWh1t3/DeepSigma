# Reconciler

Detect and resolve cross-artifact inconsistencies.

The Reconciler compares DLR entries, drift signals, and Memory Graph nodes to find mismatches between artifacts produced by the coherence_ops pipeline. It returns structured repair proposals and can auto-apply safe fixes.

**Source:** `coherence_ops/reconciler.py`

---

## Setup

No extra dependencies. Part of the `coherence_ops` package.

```python
from coherence_ops.reconciler import Reconciler, RepairKind, RepairProposal
```

---

## Usage

### Basic reconciliation

```python
from coherence_ops import DLRBuilder, DriftSignalCollector, MemoryGraph
from coherence_ops.reconciler import Reconciler

dlr = DLRBuilder()
dlr.from_episodes(episodes)

ds = DriftSignalCollector()
ds.ingest(drifts)

mg = MemoryGraph()
for ep in episodes:
    mg.add_episode(ep)

recon = Reconciler(dlr_builder=dlr, ds=ds, mg=mg)
result = recon.reconcile()

print(f"{result.auto_fixable_count} auto-fixable, {result.manual_count} manual")
for proposal in result.proposals:
    print(f"  [{proposal.kind.value}] {proposal.description}")
```

### Auto-fix safe proposals

```python
applied = recon.apply_auto_fixes()
print(f"Applied {len(applied)} auto-fixes")
```

### Export as JSON

```python
json_output = recon.to_json(indent=2)
```

---

## API Reference

### `Reconciler`

| Parameter | Type | Description |
|---|---|---|
| `dlr_builder` | `DLRBuilder` | DLR entries to check. |
| `ds` | `DriftSignalCollector` | Drift signals to check. |
| `mg` | `MemoryGraph` | Memory Graph to check against. |

All parameters are optional. Checks involving a missing component are skipped.

### Methods

| Method | Returns | Description |
|---|---|---|
| `reconcile()` | `ReconciliationResult` | Run all checks and return proposals. |
| `apply_auto_fixes()` | `list[RepairProposal]` | Reconcile, apply auto-fixable proposals, return what was applied. |
| `to_json(indent=2)` | `str` | Reconcile and serialize results to JSON. |

### `ReconciliationResult`

| Field | Type | Description |
|---|---|---|
| `run_at` | `str` | ISO timestamp of the reconciliation run. |
| `proposals` | `list[RepairProposal]` | All detected repair proposals. |
| `auto_fixable_count` | `int` | Number of proposals that can be auto-applied. |
| `manual_count` | `int` | Number of proposals requiring manual intervention. |

### `RepairProposal`

| Field | Type | Description |
|---|---|---|
| `kind` | `RepairKind` | Category of repair. |
| `target_id` | `str` | Episode ID, DLR ID, or fingerprint key. |
| `description` | `str` | Human-readable explanation. |
| `auto_fixable` | `bool` | Whether this can be auto-applied. |
| `details` | `dict` | Extra context (e.g. `dlr_id`, `fingerprint`, `patches`). |

### `RepairKind` enum

| Value | Description | Auto-fixable |
|---|---|---|
| `add_mg_node` | Episode exists in DLR but missing from Memory Graph. | Yes |
| `link_drift_to_episode` | Drift references an episode missing from Memory Graph. | No |
| `backfill_policy_stamp` | DLR entry has no policy stamp. | No |
| `flag_stale_dlr` | DLR entry references stale data. | No |
| `suggest_patch` | High-recurrence drift (3+) without resolution. | No |

---

## Reconciliation checks

1. **Missing MG nodes** -- DLR episodes not present in the Memory Graph. Auto-fix creates a backfilled node.
2. **Orphan drift** -- Drift events referencing episodes absent from the Memory Graph.
3. **Missing policy stamps** -- DLR entries without a policy stamp (audit gap).
4. **Unresolved drift** -- Drift fingerprints recurring 3+ times with recommended patches that have not been applied.

---

## CLI

```bash
# Run reconciliation and print proposals
coherence reconcile --episodes examples/episodes/ --drifts examples/drift/

# Apply auto-fixes
coherence reconcile --auto-fix

# JSON output
coherence reconcile --format json
```

Exits `0` when no proposals, `1` when proposals exist.

---

## Files

| File | Path |
|---|---|
| Source | `coherence_ops/reconciler.py` |
| DLR | `coherence_ops/dlr.py` |
| Drift signals | `coherence_ops/ds.py` |
| Memory Graph | `coherence_ops/mg.py` |
| This doc | `docs/25-reconciler.md` |
