# Quickstart

## 60-second demo
```bash
python tools/run_supervised.py   --decisionType AccountQuarantine   --policy policy_packs/packs/demo_policy_pack_v1.json   --telemetry endToEndMs=95 p99Ms=160 jitterMs=70   --context ttlBreachesCount=0 maxFeatureAgeMs=180   --verification pass   --out episodes_out
```

## What you get
- `episodes_out/<episodeId>.json` — **sealed DecisionEpisode**
- `episodes_out/<episodeId>.drift.json` — optional **DriftEvent**

## Next
- Read [Concepts](Concepts.md)
- Review [Architecture](Architecture.md)
- Pick an integration: [MCP](MCP.md), [LangChain](LangChain.md), [Power Platform](Power-Platform.md)
