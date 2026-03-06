# AuthorityOps — Module Index

## 7 OpenPQL Primitives

| # | Primitive | File | Entry Point |
|---|-----------|------|-------------|
| 1 | Policy Source | `policy_source.py` | `build_policy_source(dlr, policy_pack)` |
| 2 | Compiler | `policy_compiler.py` | `compile_from_source(source)` |
| 3 | Executable Artifacts | `artifact_builder.py` | `write_artifact(compiled, dir)` / `load_artifact(path)` |
| 4 | Runtime Gate | `runtime_gate.py` | `RuntimeGate().evaluate(compiled, request, ctx)` |
| 5 | Evidence Chain | `evidence_chain.py` | `EvidenceChain().append(entry)` |
| 6 | Audit Retrieval | `audit_retrieval.py` | `AuditRetrieval(chain).why_allowed(action_id)` |
| 7 | Seal & Hash | `seal_and_hash.py` | `compute_hash(payload)` / `verify_seal(payload, hash)` |

## Pipeline

```
ReOps DLR + PolicyPack
        ↓
  build_policy_source()     → PolicySource
        ↓
  compile_from_source()     → CompiledPolicy
        ↓
  write_artifact()          → {artifact_id}.json
  load_artifact()           → verified dict
        ↓
  RuntimeGate.evaluate()    → GateDecision (verdict)
        ↓
  EvidenceChain.append()    → chain_hash
        ↓
  AuditRetrieval.why_*()    → AuditAnswer
```

## Core Modules

| File | Purpose |
|------|---------|
| `models.py` | 15 dataclasses, 7 enums (incl. CompiledPolicy) |
| `ledger.py` | Hash-chained authority ledger |
| `authority_graph.py` | Actor/resource resolution |
| `delegation_chain.py` | Delegation chain validation |
| `reasoning_gate.py` | DLR presence, assumption freshness gates |
| `policy_runtime.py` | 11-step evaluation pipeline |
| `decision_authority_resolver.py` | Authority intersection |
| `authority_audit.py` | Hash-chained audit log |

## Demo

```bash
python -m core.examples.openpql_pipeline_demo
```

## Tests

```bash
pytest tests/test_openpql_primitives.py -v   # 40 OpenPQL tests
pytest tests/test_authority*.py -q           # 88 core authority tests
```
