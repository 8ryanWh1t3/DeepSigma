# Determinism Profile

> Rules and conventions that ensure sealed runs are fully reproducible.

## Canonical JSON

All JSON serialization uses **canonical form** (`canonical_json.canonical_dumps()`):

- Keys sorted lexicographically at every nesting level
- No trailing whitespace or optional formatting
- UTF-8 encoding, no BOM
- Numeric values: no leading zeros, no trailing decimal zeros
- Null values serialized as `null`
- No comments or trailing commas

## Timestamps

- **`committed_at`**: Fixed via `--clock` flag (ISO 8601 UTC, e.g. `2026-02-21T00:00:00Z`). Included in hash scope.
- **`observed_at`**: Wall clock time at execution. Excluded from hash scope via `exclusions` list.
- All timestamps use UTC with `Z` suffix (never `+00:00`).

## File Ordering

- Input CSV files: sorted lexicographically by path (`deterministic_io.list_files_deterministic()`)
- Prompt files: sorted by `rglob("*")` then by relative path
- Schema files: sorted by `rglob("*.json")` then by relative path
- Policy files: sorted by path

## CSV Normalization

- `deterministic_io.read_csv_deterministic()` reads all CSVs
- Row order preserved as-is (sorted by file, then row index)
- Field values are stripped of leading/trailing whitespace
- Empty fields normalize to empty string `""`

## Float Handling

- Float values (`confidence_pct`, `priority_score`) are cast via `float()` at seal time
- Python's `float()` representation is deterministic across platforms for the same input

## ID Generation

- Run IDs: `det_id("RUN", commit_hash, length=8)` — deterministic from content hash
- Entry IDs: `det_id("TLOG", commit_hash, length=8)` — deterministic from content hash
- No UUIDs (UUID v4 is random, would break determinism)

## Hash Scope

The `hash_scope` object defines exactly what is included in the `commit_hash`:

```json
{
  "scope_version": "1.0",
  "inputs": [...],
  "prompts": [...],
  "policies": [...],
  "schemas": [...],
  "parameters": {
    "clock": "2026-02-21T00:00:00Z",
    "deterministic": true
  },
  "exclusions": [
    "observed_at",
    "artifacts_emitted"
  ]
}
```

### Included in Hash Scope
- All input file paths and SHA-256 hashes
- All prompt file paths and SHA-256 hashes
- All schema file paths and SHA-256 hashes
- Policy file path, SHA-256 hash, and version
- Clock parameter value
- Deterministic flag

### Excluded from Hash Scope
- `observed_at` — wall clock, varies per run
- `artifacts_emitted` — output paths, vary per environment

## Merkle Commitments

- `inputs_commitments` is **derived from** hash_scope data (same leaf hashes)
- It is **not included in** hash_scope (would be circular)
- Leaf hashes are sorted before tree construction
- Odd leaf count: last leaf duplicated

## Audit Checks

The `determinism_audit.py` tool verifies:

| Check | Description |
|-------|-------------|
| `hash_scope.present` | hash_scope object exists |
| `hash_scope.clock_fixed` | clock parameter is non-null |
| `hash_scope.deterministic_flag` | deterministic parameter is true |
| `exclusions.observed_at` | observed_at in exclusion list |
| `ids.run_id_deterministic` | run_id matches `det_id("RUN", commit_hash)` |
| `ids.no_uuid` | No UUID v4 patterns found |
| `timestamps.committed_at_matches_clock` | committed_at equals clock parameter |
| `commitments.present` | inputs_commitments exists (v1.3+) |
| `canonical.json_valid` | Re-serialization matches original |

## Reproducing a Sealed Run

```bash
# Exact reproduction:
python src/tools/reconstruct/seal_bundle.py \
    --decision-id DEC-001 \
    --clock 2026-02-21T00:00:00Z \
    --deterministic true \
    --user ci

# Verify determinism:
python src/tools/reconstruct/determinism_audit.py \
    --sealed artifacts/sealed_runs/RUN-xxx_20260221T000000Z.json
```

Two runs with identical inputs and clock produce identical `commit_hash` values.
