# Prompt OS Scripts

Tools for validating, exporting, and demoing Prompt OS v2 data.

## Scripts

| Script | Purpose |
|--------|---------|
| `validate_prompt_os.py` | CSV ↔ Schema parity validator |
| `validate_prompt_os.sh` | Shell runner for the validator |
| `export_sealed_run.py` | Export a single sealed run from LLM_OUTPUT CSV to JSON |
| `drift_to_patch_demo.py` | One-command Drift → Patch hero loop |
| `export_for_snowflake.py` | Snowflake-ready export bundle generator |

## Quick Commands

```bash
# Validate CSVs against schema
python src/tools/prompt_os/validate_prompt_os.py

# Export a sealed run
python src/tools/prompt_os/export_sealed_run.py --run-id RUN-001

# Run the hero loop (drift detection → patch → telemetry → sealed JSON)
python src/tools/prompt_os/drift_to_patch_demo.py

# Export Snowflake bundle
python src/tools/prompt_os/export_for_snowflake.py
```

## Related

- [docs/prompt_os/README.md](../../docs/prompt_os/README.md) — Full Prompt OS documentation
- [.github/workflows/prompt_os_validate.yml](../../.github/workflows/prompt_os_validate.yml) — CI workflow
