[![CI](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml/badge.svg)](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deepsigma)](https://pypi.org/project/deepsigma/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

# DeepSigma

DeepSigma is institutional decision infrastructure: capture intent, run governed execution, detect drift, and patch safely.

This repository is intentionally structured with two modes:

- **Core mode (active at repo root):** minimal, demo-first, deterministic.
- **Enterprise mode (parked):** full platform surface preserved under [`_park_enterprise/`](_park_enterprise/).

## Quick Start (Core)

```bash
pip install deepsigma
./run_money_demo.sh
```

What this gives you immediately:

- Drift -> Patch demo run
- Contract test verification (`tests/test_money_demo.py`)
- Deterministic artifacts in `docs/examples/demo-stack/drift_patch_cycle_run/`

Optional baseline proof:

```bash
make core-baseline
```

Outputs:

- `docs/examples/demo-stack/CORE_BASELINE_REPORT.json`
- `docs/examples/demo-stack/CORE_BASELINE_REPORT.md`

## Operating Modes

### Core Mode

Use Core mode when you need fast adoption and low cognitive load.

Active Core surface at repo root:

- `run_money_demo.sh`
- `src/coherence_ops/`
- `docs/examples/demo-stack/`
- `tests/test_money_demo.py`

### Enterprise Mode

Use Enterprise mode when you need connectors, dashboards, extended security, broader telemetry, and integration-heavy workflows.

Enterprise surfaces are preserved in:

- [`_park_enterprise/README.md`](_park_enterprise/README.md)

Examples of parked modules:

- `_park_enterprise/dashboard/`
- `_park_enterprise/docker/`
- `_park_enterprise/release_kpis/`
- `_park_enterprise/schemas/`
- `_park_enterprise/scripts/`
- `_park_enterprise/src/` (non-core packages)
- `_park_enterprise/docs/` (full enterprise docs)

## Full Platform References

For the full-platform docs and architecture map, use parked docs directly:

- `_park_enterprise/docs/positioning/positioning_manifesto.md`
- `_park_enterprise/docs/positioning/executive_briefing_one_page.md`
- `_park_enterprise/docs/release/`
- `_park_enterprise/docs/security/`
- `_park_enterprise/docs/mermaid/`

## Repo Intent

- Keep root focused on a reliable first proof.
- Keep enterprise depth available without deleting capability.
- Expand from Core into Enterprise intentionally, not by drift.

## License

[MIT](LICENSE)
