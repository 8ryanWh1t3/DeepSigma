# Evidence Chain Spec (Primitive 5) + Audit Retrieval (Primitive 6)

## Evidence Chain (Primitive 5)

### Purpose

Append-only, hash-chained JSONL evidence log capturing every authority evaluation with full artifact and assumption context.

### Module

`src/core/authority/evidence_chain.py`

### EvidenceEntry Fields

| Field | Type | Description |
|-------|------|-------------|
| `evidence_id` | str | `EV-{12hex}` (auto-generated if empty) |
| `gate_id` | str | RuntimeGate ID that produced the verdict |
| `action_id` | str | Action being evaluated |
| `actor_id` | str | Actor requesting the action |
| `resource_id` | str | Resource targeted by the action |
| `verdict` | str | AuthorityVerdict value |
| `evaluated_at` | str | ISO 8601 timestamp |
| `artifact_id` | str | CompiledPolicy artifact ID |
| `policy_hash` | str | Deterministic hash of the compiled rules |
| `dlr_ref` | str | Decision Log Record reference |
| `assumptions_snapshot` | dict | Snapshot of assumption state at evaluation time |
| `failed_checks` | list | Pipeline steps that failed |
| `passed_checks` | list | Pipeline steps that passed |
| `chain_hash` | str | SHA-256 hash of this entry (computed on append) |
| `prev_chain_hash` | str | Link to previous entry's chain_hash |

### JSONL Format

Each entry is one JSON line. Entries are appended without rewriting the file. Example:

```jsonl
{"evidence_id":"EV-abc123","gate_id":"RGATE-def456","action_id":"ACT-001","verdict":"ALLOW","chain_hash":"sha256:...","prev_chain_hash":null,...}
{"evidence_id":"EV-ghi789","gate_id":"RGATE-jkl012","action_id":"ACT-002","verdict":"BLOCK","chain_hash":"sha256:...","prev_chain_hash":"sha256:...",... }
```

### Chain Verification

`EvidenceChain.verify() -> bool`

Walks the full chain checking:
1. First entry has `prev_chain_hash = None`
2. Each subsequent entry's `prev_chain_hash` matches the previous entry's `chain_hash`
3. Each entry's `chain_hash` matches the recomputed hash (with `chain_hash` zeroed)

---

## Audit Retrieval (Primitive 6)

### Purpose

Forensic query interface over the evidence chain. Answers natural-language audit questions with structured `AuditAnswer` responses.

### Module

`src/core/authority/audit_retrieval.py`

### Query Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `why_allowed(action_id)` | AuditAnswer | Passed checks and artifact used |
| `why_blocked(action_id)` | AuditAnswer | Which check failed and terminal verdict |
| `which_rule_fired(action_id)` | AuditAnswer | Specific constraint that decided the verdict |
| `which_assumption_failed(action_id)` | AuditAnswer | Stale assumptions from the snapshot |
| `which_policy_hash(action_id)` | AuditAnswer | Policy hash used for this evaluation |
| `actor_history(actor_id)` | list[AuditAnswer] | All evaluations for an actor, chronological |
| `resource_history(resource_id)` | list[AuditAnswer] | All evaluations for a resource, chronological |

### AuditAnswer Model

```python
@dataclass
class AuditAnswer:
    query_type: str         # e.g. "why_allowed", "why_blocked"
    action_id: str
    found: bool             # whether matching entries were found
    verdict: str            # AuthorityVerdict value
    detail: str             # human-readable explanation
    evidence: Optional[dict] # structured evidence payload
    entries: list[dict]     # raw matching entries
```
