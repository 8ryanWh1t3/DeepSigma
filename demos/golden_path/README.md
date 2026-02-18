# Golden Path

**One command. One outcome. No ambiguity.**

Proves DeepSigma can take real enterprise exhaust, normalize it, extract claims, seal a decision episode, detect drift, emit a patch, and recall via IRIS — end to end.

## The 7-Step Loop

| Step | What | Output |
|------|------|--------|
| 1. Connect | Pull canonical records from source | `canonical_records.json` |
| 2. Normalize | Assemble into schema-valid episode | `episode.json` |
| 3. Extract | Rule-based atomic claims + evidence | `claims.json` |
| 4. Seal | DLR + RS + DS + MG + CoherenceReport | `coherence_report.json` |
| 5. Drift | Compare baseline vs delta records | `drift_report.json` |
| 6. Patch | Emit patches, re-score | `patch.json` |
| 7. Recall | IRIS: WHY, WHAT_CHANGED, STATUS | `iris_*.json` |

## Quick Start (Fixture Mode)

No credentials required:

```bash
python -m demos.golden_path \
  --source sharepoint \
  --fixture demos/golden_path/fixtures/sharepoint_small
```

Or via the CLI:

```bash
coherence golden-path sharepoint \
  --fixture demos/golden_path/fixtures/sharepoint_small
```

## Live Mode

Set environment variables for your connector, then run without `--fixture`:

```bash
# SharePoint
export SP_TENANT_ID=... SP_CLIENT_ID=... SP_CLIENT_SECRET=... SP_SITE_ID=...
python -m demos.golden_path --source sharepoint --list-id "Documents"

# Snowflake
export SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_TOKEN=...
python -m demos.golden_path --source snowflake --sql "SELECT * FROM decisions LIMIT 10"

# Dataverse
export DV_ENVIRONMENT_URL=... DV_CLIENT_ID=... DV_CLIENT_SECRET=... DV_TENANT_ID=...
python -m demos.golden_path --source dataverse --table incidents

# AskSage
export ASKSAGE_EMAIL=... ASKSAGE_API_KEY=...
python -m demos.golden_path --source asksage --prompt "What are our current risk factors?"
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | (required) | `sharepoint`, `snowflake`, `dataverse`, `asksage` |
| `--fixture` | None | Path to fixture directory (enables offline mode) |
| `--episode-id` | `gp-demo` | Custom episode ID |
| `--output` | `./golden_path_output` | Output directory |
| `--json` | false | Output JSON result |
| `--supervised` | false | Pause before patch step |

## Output Structure

```
golden_path_output/
├── step_1_connect/canonical_records.json
├── step_2_normalize/episode.json
├── step_3_extract/claims.json
├── step_4_seal/{dlr,rs,ds,mg,coherence_report}.json
├── step_5_drift/{delta_records,drift_report}.json
├── step_6_patch/{patch,mg_patched,coherence_report_patched}.json
├── step_7_recall/{iris_why,iris_what_changed,iris_status}.json
└── summary.json
```

## Tests

```bash
pytest tests/test_golden_path.py -v
```
