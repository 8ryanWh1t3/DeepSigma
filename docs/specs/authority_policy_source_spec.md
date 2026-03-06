# Policy Source Spec (Primitive 1)

## Purpose

Wraps a ReOps DLR + PolicyPack into a validated, hashable object that serves as the single input to the OpenPQL compilation pipeline.

## Module

`src/core/authority/policy_source.py`

## Data Model

```python
@dataclass
class PolicySource:
    source_id: str              # "PSRC-{12hex}"
    dlr: Dict[str, Any]         # ReOps Decision Log Record
    policy_pack: Dict[str, Any] # Policy configuration
    claims: List[Dict]          # Extracted claims list
    created_at: str             # ISO 8601 timestamp
    version: str                # "1.0.0"
    source_hash: str            # "sha256:<hex>" deterministic hash
```

## Construction

`build_policy_source(dlr, policy_pack, claims?) -> PolicySource`

1. Extract `dlrId` from DLR (required — raises `ValueError` if empty)
2. Extract claims from DLR if not provided explicitly
3. Compute deterministic `source_hash` from `{dlr_id, policy_pack_id, claim_count}`
4. Return `PolicySource` with generated `source_id`

## Validation

`validate_policy_source(source) -> (bool, list[str])`

Checks:
- `dlr` is not empty
- `dlr` has a `dlrId`
- `policy_pack` is not empty
- `source_hash` is present

## Mapping from ReOps

| ReOps Field | PolicySource Field |
|-------------|-------------------|
| `dlr.dlrId` | `source.dlr` (full DLR preserved) |
| `dlr.claims.{action}` | `source.claims` (flattened list) |
| Policy pack by action type | `source.policy_pack` |

## Hash Determinism

Same DLR + same policy pack = same `source_hash`. The hash is computed over `{dlr_id, policy_pack_id, claim_count}` using `seal_and_hash.compute_hash()`.
