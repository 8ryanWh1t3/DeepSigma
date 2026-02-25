# DeepSigma Edition Contract

This file is the canonical boundary ledger between CORE and ENTERPRISE.

## Scope

- One product line, one version stream.
- Two editions:
  - CORE (default)
  - ENTERPRISE (optional overlay)

## Source Layout Contract

- CORE code lives in:
  - `src/core/`
  - `src/core/schemas/` (all core data schemas: episode, DLR, drift, DTE, etc.)
- ENTERPRISE code lives in:
  - `enterprise/src/` (adapters, mesh, demos, engine, tools, governance, etc.)
  - `enterprise/dashboard/`
  - `enterprise/docs/`
  - `enterprise/scripts/`
  - `enterprise/release_kpis/`

## Packaging Contract

- CORE package:
  - `pip install deepsigma`
  - Ships `core` Python package + schemas
  - CLI: `coherence` (or `python -m core`)
- ENTERPRISE overlay package:
  - `pip install deepsigma-enterprise` (requires `deepsigma` core)
  - Ships all enterprise sub-packages (adapters, mesh, demos, engine, etc.)
  - CLI: `deepsigma`
  - Extras: `azure`, `excel`, `exhaust-llm`, `langgraph`, `local`, `mesh`, `openclaw`, `otel`, `postgresql`, `rdf`, `snowflake`, `viz`, `all`

## Artifact Contract

- CORE artifact:
  - `dist/deepsigma-core-vX.Y.Z.zip`
- ENTERPRISE artifact:
  - `dist/deepsigma-enterprise-vX.Y.Z.zip`

## CI Contract

- CORE always-on gates:
  - `make edition-guard`
  - `make core-ci` (money demo + baseline + core tests)
- ENTERPRISE optional gate:
  - `make enterprise-ci` (enterprise demo + enterprise tests)
- Guardrail:
  - CORE must not import enterprise modules (`edition-guard`).
  - Guard checks all 12 enterprise sub-package names via AST parsing.

## Hard Rule

**CORE never imports ENTERPRISE.** The edition guard (`enterprise/scripts/edition_guard.py`) enforces this by scanning `src/core/` for imports from any enterprise sub-package: `adapters`, `credibility_engine`, `deepsigma`, `demos`, `engine`, `enterprise`, `governance`, `mdpt`, `mesh`, `services`, `tenancy`, `tools`, `verifiers`.

## Change Rules

- Changes that widen CORE scope must update this file.
- Any move of files between CORE and ENTERPRISE must update this file.
- CI gate changes must preserve CORE always-on and ENTERPRISE optional behavior unless explicitly versioned and approved.
