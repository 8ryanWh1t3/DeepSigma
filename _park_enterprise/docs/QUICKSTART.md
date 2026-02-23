# Quickstart (Under 5 Minutes)

This walkthrough gets you from zero to a working lattice with sample claims, a drift scenario, IRIS queries, and a Trust Scorecard.

## 1) Create a fresh environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install deepsigma
```

## 2) Scaffold a starter project

```bash
deepsigma init my-project
cd my-project
```

Generated content includes:
- `data/sample_claims.json`
- `data/sample_drift.json`
- `scenarios/drift_scenario.md`
- `queries/iris_queries.md`
- `Makefile` with runnable demo targets

## 3) Run the demo flow

```bash
make demo
```

This writes:
- `out/score.json` (coherence score output)
- `out/iris_why.json` (WHY retrieval)
- `out/iris_drift.json` (WHAT_DRIFTED retrieval)
- `out/trust_scorecard.json` (trust metrics + SLO checks)

## 4) Verify key outputs

```bash
cat out/trust_scorecard.json
cat out/iris_why.json
```

## Next Steps

1. Connector setup: `docs/CONNECTOR_SDK.md`
2. OpenClaw policy modules: `adapters/openclaw/`
3. Dashboard: `dashboard/` and `docs/24-dashboard-api.md`
4. API reference: `docs/api/index.html`
