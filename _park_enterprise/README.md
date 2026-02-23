# DeepSigma Enterprise Park

This directory holds the full enterprise surface that was removed from the strict Core root layout.

## Why this exists

- Keep `DeepSigma Core` small and demo-first at repo root.
- Preserve enterprise assets without deleting them.
- Allow controlled reintroduction of enterprise components later.

## What is parked here

Examples:

- `artifacts/`, `dashboard/`, `docker/`, `release_kpis/`, `schemas/`, `scripts/`
- `src/` enterprise packages outside Core
- enterprise docs, tests, and roadmap content

## Core boundary

The active Core surface remains at repo root:

- `run_money_demo.sh`
- `src/coherence_ops/`
- `docs/examples/demo-stack/`
- `tests/test_money_demo.py`

## Restore guidance

To restore enterprise components into root, move specific directories out of `_park_enterprise/` in a dedicated branch and update:

1. `README.md`
2. `pyproject.toml`
3. `.github/workflows/`

Avoid broad moves without an explicit scope decision, or Core compliance will drift.
