[![CI](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml/badge.svg)](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deepsigma)](https://pypi.org/project/deepsigma/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

# DeepSigma

DeepSigma is institutional decision infrastructure: capture intent, run governed execution, detect drift, and patch safely.

This repository ships as one product line with one version and two editions:

- **CORE edition:** minimal, demo-first, deterministic (`pip install deepsigma`)
- **ENTERPRISE edition:** extended adapters, dashboards, and ops surfaces (repo-native under `enterprise/`)

Edition boundary ledger:
- `EDITION_DIFF.md`

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
- `src/core/`
- `docs/examples/demo-stack/`
- `tests/test_money_demo.py`

### Enterprise Mode

Use Enterprise mode when you need connectors, dashboards, extended security, broader telemetry, and integration-heavy workflows.

Dependency note:
- `pip install "deepsigma[enterprise]"` installs enterprise runtime extras used by telemetry/radar tooling.
- Full enterprise code surfaces are repository-native under `enterprise/` and are run from source in this repo.

Enterprise surfaces are first-class under:

- [`enterprise/README.md`](enterprise/README.md)

Examples of parked modules:

- `enterprise/dashboard/`
- `enterprise/docker/`
- `enterprise/release_kpis/`
- `enterprise/schemas/`
- `enterprise/scripts/`
- `enterprise/src/` (non-core packages)
- `enterprise/docs/` (full enterprise docs)

Run the enterprise wedge:

```bash
make enterprise-demo
make test-enterprise
```

## Release Artifacts

Build both edition artifacts from one version line:

```bash
make release-artifacts
```

Outputs in `dist/`:
- `deepsigma-core-vX.Y.Z.zip`
- `deepsigma-enterprise-vX.Y.Z.zip`

## Full Platform References

For the full-platform docs and architecture map, use parked docs directly:

- `enterprise/docs/positioning/positioning_manifesto.md`
- `enterprise/docs/positioning/executive_briefing_one_page.md`
- `enterprise/docs/release/`
- `enterprise/docs/security/`
- `enterprise/docs/mermaid/`

## Repo Intent

- Keep root focused on a reliable first proof.
- Keep enterprise depth available without deleting capability.
- Expand from Core into Enterprise intentionally, not by drift.

## License

[MIT](LICENSE)
