# One-command demo: run_supervised.py

This is the fastest way to demonstrate the product loop:

**Policy Pack → Degrade Ladder → Verification → Seal Episode → Drift (optional)**

## Example
```bash
python tools/run_supervised.py   --decisionType AccountQuarantine   --policy policy_packs/packs/demo_policy_pack_v1.json   --telemetry endToEndMs=95 p99Ms=160 jitterMs=70   --context ttlBreachesCount=0 maxFeatureAgeMs=180   --verification pass   --out episodes_out
```

Outputs:
- `episodes_out/<episodeId>.json` (sealed DecisionEpisode)
- `episodes_out/<episodeId>.drift.json` (only when drift is detected)

Replace the stubs with real adapters (LangChain / Foundry / Power Platform / MCP) to move from demo → production.
