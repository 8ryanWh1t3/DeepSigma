[![CI](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml/badge.svg)](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deepsigma)](https://pypi.org/project/deepsigma/)
[![GHCR Pulls](https://img.shields.io/docker/pulls/ghcr.io/8ryanwh1t3/deepsigma)](https://github.com/8ryanWh1t3/DeepSigma/pkgs/container/deepsigma)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/8ryanWh1t3/DeepSigma)](https://github.com/8ryanWh1t3/DeepSigma/releases/latest)

<div align="center">

# Σ OVERWATCH

**Current pilot release:** v2.0.3  
See: [docs/release/RELEASE_NOTES_v2.0.3.md](docs/release/RELEASE_NOTES_v2.0.3.md)

## Repo Radar KPI (latest)
[![Repo KPI Badge](https://github.com/8ryanWh1t3/DeepSigma/blob/main/release_kpis/badge_latest.svg?raw=1)](https://github.com/8ryanWh1t3/DeepSigma/blob/main/release_kpis/radar_v2.0.3.png?raw=1)

- Current release radar: [release_kpis/radar_v2.0.3.png](https://github.com/8ryanWh1t3/DeepSigma/blob/main/release_kpis/radar_v2.0.3.png?raw=1)
- Composite release radar: [release_kpis/radar_composite_latest.png](https://github.com/8ryanWh1t3/DeepSigma/blob/main/release_kpis/radar_composite_latest.png?raw=1)
- Composite release delta table: [release_kpis/radar_composite_latest.md](https://github.com/8ryanWh1t3/DeepSigma/blob/main/release_kpis/radar_composite_latest.md)
- Gate report: [release_kpis/KPI_GATE_REPORT.md](https://github.com/8ryanWh1t3/DeepSigma/blob/main/release_kpis/KPI_GATE_REPORT.md)
- Issue label gate: [release_kpis/ISSUE_LABEL_GATE_REPORT.md](https://github.com/8ryanWh1t3/DeepSigma/blob/main/release_kpis/ISSUE_LABEL_GATE_REPORT.md)
- KPI history: [release_kpis/history.json](https://github.com/8ryanWh1t3/DeepSigma/blob/main/release_kpis/history.json)

**Institutional Decision Infrastructure**

*Trust layer for agentic AI: verify before act, seal what happened, detect drift, ship patches.*

</div>

---

## What It Does

Organizations make thousands of decisions. Almost none are structurally recorded with their reasoning, evidence, or assumptions. When leaders leave, conditions change, or AI accelerates decisions 100x — governance fails silently.

**Σ OVERWATCH** fills this gap with three primitives:

- **Truth** — Decision Ledger Records (DLR) capture what was decided, by whom, with what evidence
- **Reasoning** — Reasoning Scaffolds (RS) capture why — claims, counter-claims, weights
- **Memory** — Decision Scaffolds + Memory Graphs (DS + MG) make institutional knowledge queryable

When assumptions decay, **Drift** fires. When drift exceeds tolerance, a **Patch** corrects it. This is the **Drift → Patch loop** — continuous self-correction.

---

## Quick Start

```bash
pip install deepsigma

# One-command Money Demo (recommended first run)
make demo

# Health check
deepsigma doctor

# Score coherence (0–100, A–F)
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json

# Drift → Patch canonical entrypoint
python -m coherence_ops.examples.drift_patch_cycle

# Full 7-step Golden Path (no credentials needed)
deepsigma golden-path sharepoint \
  --fixture src/demos/golden_path/fixtures/sharepoint_small --clean

# Retention lifecycle sweep (cron-friendly)
deepsigma retention sweep --tenant tenant-alpha
```

## Golden-Path Proof Artifacts

![Credibility Index dashboard proof](docs/assets/dashboard_credibility_index.svg)
![Drift detection and patch proof](docs/assets/dashboard_drift_patch.svg)

```bash
# Golden Path run (ingest -> drift -> patch -> recall)
PYTHONPATH=src python -m tools.golden_path_cli golden-path sharepoint \
  --fixture src/demos/golden_path/fixtures/sharepoint_small \
  --output golden_path_output --clean

# Trust Scorecard (includes WHY retrieval SLO check)
PYTHONPATH=src python -m tools.trust_scorecard \
  --input golden_path_output \
  --output golden_path_output/trust_scorecard.json
```

```text
============================================================
  GOLDEN PATH
============================================================
  [1] CONNECT              PASS
  [2] NORMALIZE            PASS
  [3] EXTRACT              PASS
  [4] SEAL                 PASS
  [5] DRIFT                PASS
  [6] PATCH                PASS
  [7] RECALL               PASS
...
  IRIS:       WHY=RESOLVED, WHAT_CHANGED=RESOLVED, STATUS=RESOLVED
  Drift:      6 events
  Patch:      applied
============================================================
Trust Scorecard written to golden_path_output/trust_scorecard.json
  SLOs:    ALL PASS
```

Trust Scorecard highlights from the same run:
- `iris_why_latency_ms`: `1.4` (`<= 60000` target, retrieval <= 60s)
- `patch_applied`: `true`
- `drift_events_detected`: `6`
- `all_steps_passed`: `true`

---

## Court-Grade Proof (60 seconds)

```bash
# Seal + sign + authority bind + transparency log + pack
python src/tools/reconstruct/seal_and_prove.py \
    --decision-id DEC-001 --clock 2026-02-21T00:00:00Z \
    --sign-algo hmac --sign-key-id ds-dev --sign-key "$KEY" \
    --auto-authority --pack-dir /tmp/pack

# Verify everything in one command:
python src/tools/reconstruct/verify_pack.py --pack /tmp/pack --key "$KEY"
```

---

## Key Capabilities

| Capability | Description | Docs |
|---|---|---|
| **Coherence Ops CLI** | Score, audit, query, reconcile decision artifacts | [CLI Reference](docs/CLI.md) |
| **Golden Path** | 7-step end-to-end proof loop | [Golden Path](demos/golden_path/README.md) |
| **Credibility Engine** | Institutional-scale claim lattice with formal scoring | [Engine Docs](docs/credibility-engine/) |
| **Trust Scorecard** | Measurable SLOs from every Golden Path run | [Spec](schemas/core/trust_scorecard_v1.md) |
| **Excel-first BOOT** | Govern decisions in a shared workbook — no code required | [BOOT Protocol](docs/excel-first/WORKBOOK_BOOT_PROTOCOL.md) |
| **MDPT** | Multi-Dimensional Prompt Toolkit for governed prompt ops | [MDPT Docs](src/mdpt/README.md) |
| **Court-Grade Admissibility** | Seal-and-prove pipeline: Merkle commitments, transparency log, multi-sig witness, hardware key hooks | [Admissibility Levels](docs/reconstruct/ADMISSIBILITY_LEVELS.md) |
| **MCP Server** | Model Context Protocol server with auth + rate limiting | [MCP Adapter](adapters/mcp/) |
| **RDF/SPARQL** | Semantic lattice queries via in-process SPARQL 1.1 | [SPARQL Service](services/sparql_service.py) |
| **Dashboard** | React dashboard with Trust Scorecard + Zustand store | [Dashboard](dashboard/) |

## Connectors

All connectors conform to the [Connector Contract v1.0](schemas/core/connector_contract_v1.md).

| Connector | Transport | Docs |
|---|---|---|
| SharePoint | Graph API | [docs](docs/26-sharepoint-connector.md) |
| Power Platform | Dataverse Web API | [docs](docs/27-power-platform-connector.md) |
| AskSage | REST API | [docs](docs/28-asksage-connector.md) |
| Snowflake | Cortex + SQL API | [docs](docs/29-snowflake-connector.md) |
| LangGraph | LangChain Callback | [docs](docs/23-langgraph-adapter.md) |
| OpenClaw | WASM Sandbox | [docs](adapters/openclaw/) |
| Local LLM | llama.cpp / OpenAI-compatible | [docs](docs/30-local-inference.md) |

---

## Repo Structure

```
DeepSigma/
├── src/                 # 12 Python packages (all source code)
│   ├── coherence_ops/   #   Core library + CLI
│   ├── engine/          #   Compression, degrade ladder, supervisor
│   ├── adapters/        #   MCP, SharePoint, Snowflake, LangGraph, OpenClaw, AskSage
│   ├── deepsigma/       #   Unified product CLI
│   ├── demos/           #   Golden Path, Excel-first Money Demo
│   ├── mdpt/            #   MDPT tools + Power App starter kit
│   └── ...              #   credibility_engine, services, mesh, governance, tenancy, verifiers, tools
├── tests/               # 1250+ tests, fixtures, datasets
├── docs/                # Documentation + examples (canonical, mermaid, lattices, etc.)
├── dashboard/           # React dashboard + API server
├── schemas/             # JSON schemas (core engine + Prompt OS)
├── artifacts/           # Workbooks, templates, sealed runs, sample data
├── prompts/             # Canonical prompts + Prompt OS control prompts
└── .github/             # CI/CD workflows
```

---

## Documentation

| | |
|---|---|
| [START_HERE.md](docs/START_HERE.md) | Front door |
| [HERO_DEMO.md](docs/HERO_DEMO.md) | 5-minute hands-on walkthrough |
| [NAV.md](docs/NAV.md) | Full navigation index |
| [ABOUT.md](docs/ABOUT.md) | Reality Await Layer (RAL) |
| [OPS_RUNBOOK.md](docs/OPS_RUNBOOK.md) | Operations + incident playbooks |
| [STABILITY.md](docs/STABILITY.md) | Versioning policy + stability guarantees |
| [docs/99-docs-map.md](docs/99-docs-map.md) | Complete docs map |

---

## Excel Prompt OS v2

Structured cognition workbook for institutional decision-making — no code required.

- **Workbook:** [`artifacts/excel/Coherence_Prompt_OS_v2.xlsx`](artifacts/excel/Coherence_Prompt_OS_v2.xlsx)
- **Quickstart:** [`docs/prompt_os/README.md`](docs/prompt_os/README.md)
- **Prompts:** [`docs/prompt_os/PROMPTS.md`](docs/prompt_os/PROMPTS.md)
- **Diagram:** [`docs/prompt_os/diagrams/prompt_os_flow.mmd`](docs/prompt_os/diagrams/prompt_os_flow.mmd)

## Prompts

- **Canonical Prompts v1:** [`prompts/canonical/`](prompts/canonical/) — Executive Analysis, Reality Assessment
- **Prompt Index:** [`prompts/README.md`](prompts/README.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)

---

<div align="center">

**Σ OVERWATCH**
*We don't sell agents. We sell the ability to trust them.*

</div>
