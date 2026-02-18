# Schema Validation

Runtime JSON Schema validation for ingest boundaries.

The schema validator lazy-compiles schemas from `specs/*.schema.json` and validates payloads at episode ingestion, policy pack loading, drift acceptance, and MCP input. All schemas use JSON Schema Draft 2020-12 with `$ref` resolution against local spec files.

**Source:** `engine/schema_validator.py`

---

## Setup

Requires `jsonschema` and `referencing`:

```bash
pip install jsonschema referencing
```

Enable runtime validation via environment variable:

```bash
export DEEPSIGMA_VALIDATE_SCHEMAS=1
```

---

## Usage

### Validate a payload

```python
from engine.schema_validator import validate

result = validate(episode_dict, "episode")
if not result.valid:
    for err in result.errors:
        print(f"{err.path}: {err.message}")
```

### Check if validation is enabled

```python
from engine.schema_validator import is_validation_enabled

if is_validation_enabled():
    result = validate(payload, "drift")
```

### Clear the validator cache (testing)

```python
from engine.schema_validator import clear_cache

clear_cache()
```

---

## API Reference

### `validate(payload, schema_name) -> ValidationResult`

| Parameter | Type | Description |
|---|---|---|
| `payload` | `dict` | The JSON-serializable dict to validate. |
| `schema_name` | `str` | Name of the schema (see supported schemas below). |

Returns a `ValidationResult`. If the schema file is not found, returns `valid=True` (permissive fallback).

### `ValidationResult`

| Field | Type | Description |
|---|---|---|
| `valid` | `bool` | `True` when no errors were found. |
| `errors` | `list[SchemaError]` | List of validation errors. |
| `schema_name` | `str` | The schema that was validated against. |

### `SchemaError`

| Field | Type | Description |
|---|---|---|
| `path` | `str` | JSON pointer to the failing field (e.g. `context/ttlMs`). |
| `message` | `str` | Human-readable error message. |
| `schema_path` | `str` | JSON pointer into the schema definition. |

### Utility functions

| Function | Description |
|---|---|
| `is_validation_enabled()` | Returns `True` when `DEEPSIGMA_VALIDATE_SCHEMAS` is `1`, `true`, or `yes`. |
| `clear_cache()` | Clears the compiled validator and registry cache. Useful in test fixtures. |

---

## Supported schemas

| `schema_name` | Schema file | Used for |
|---|---|---|
| `episode` | `specs/episode.schema.json` | DecisionEpisode payloads |
| `drift` | `specs/drift.schema.json` | DriftEvent payloads |
| `dte` | `specs/dte.schema.json` | Decision Timing Envelope specs |
| `canonical_record` | `specs/canonical_record.schema.json` | Connector record envelopes |
| `dlr` | `specs/dlr.schema.json` | Decision Log Records |
| `policy_pack` | `policy_packs/policy_pack.schema.json` | Policy pack definitions |

External `$ref` URLs prefixed with `https://sigma-overwatch.dev/schemas/` resolve to local `specs/` files automatically.

---

## CLI

```bash
# Validate a single file
coherence schema validate --schema episode --file examples/episodes/ep_001.json

# Validate all episodes in a directory
coherence schema validate --schema episode --dir examples/episodes/

# Validate with verbose error output
coherence schema validate --schema drift --file sample_drift.json --verbose
```

Exits `0` on valid, `1` on validation errors.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DEEPSIGMA_VALIDATE_SCHEMAS` | *(unset)* | Set to `1`/`true`/`yes` to enable runtime validation. |

---

## Files

| File | Path |
|---|---|
| Source | `engine/schema_validator.py` |
| Schema directory | `specs/` |
| This doc | `docs/22-schema-validation.md` |
