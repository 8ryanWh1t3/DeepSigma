# DeepSigma Core

Run this first:

```bash
./run_money_demo.sh
```

DeepSigma Core is the compressed adoption path focused on one wedge: Drift -> Patch.

## What You Get

- Deterministic Money Demo artifacts in `docs/examples/demo-stack/drift_patch_cycle_run/`
- Contract test coverage for the demo (`tests/test_money_demo.py`)
- Deterministic baseline proof report via:

```bash
make core-baseline
```

Outputs:
- `docs/examples/demo-stack/CORE_BASELINE_REPORT.json`
- `docs/examples/demo-stack/CORE_BASELINE_REPORT.md`

## Core Commands

```bash
make demo
make core-baseline
```

## Repository Layout (Core)

- `run_money_demo.sh`
- `src/coherence_ops/`
- `docs/examples/demo-stack/`
- `tests/test_money_demo.py`

## Enterprise Archive

Non-core platform surface has been parked under `_park_enterprise/` for Option A compression.
