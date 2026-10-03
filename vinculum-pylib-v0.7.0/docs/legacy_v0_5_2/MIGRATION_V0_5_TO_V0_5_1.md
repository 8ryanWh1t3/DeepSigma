# Migration — v0.5.0 → v0.5.1

## Compatibility

Existing v0.5.0 calls continue to work.

```python
result = VinculumEngine().score(obj)
```

The original `Sigma_V`, `vinculum_score`, `tension_index`, and `usable_value` remain.

## New result fields

```text
reconciliation_status
semantic_record_tension
comparison_coverage
reconciled_usable_value
semantic_reconciliation
tension_model
```

## New extension point

```python
VinculumEngine(meaning_registry=custom_registry)
```

No migration is required unless you want semantic determinization and cross-object comparison.
