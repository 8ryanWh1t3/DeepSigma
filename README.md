[![CI](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml/badge.svg)](https://github.com/8ryanWh1t3/DeepSigma/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deepsigma)](https://pypi.org/project/deepsigma/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

<div align="center">

# Σ OVERWATCH

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

# Health check
deepsigma doctor

# Score coherence (0–100, A–F)
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json

# Drift → Patch in 60 seconds
python -m coherence_ops.examples.drift_patch_cycle

# Full 7-step Golden Path (no credentials needed)
deepsigma golden-path sharepoint \
  --fixture src/demos/golden_path/fixtures/sharepoint_small --clean
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
├── tests/               # 1050+ tests, fixtures, datasets
├── docs/                # Documentation + examples (canonical, mermaid, lattices, etc.)
├── dashboard/           # React dashboard + API server
├── schemas/             # JSON schemas (core engine + Prompt OS)
├── artifacts/           # Workbooks, templates, sealed runs
├── prompts/             # Canonical prompts + Prompt OS control prompts
├── sample_data/         # Demo-ready CSV sample data
├── scripts/             # Validation and export scripts
└── .github/             # CI/CD workflows
```

---

## Documentation

| | |
|---|---|
| [START_HERE.md](START_HERE.md) | Front door |
| [HERO_DEMO.md](HERO_DEMO.md) | 5-minute hands-on walkthrough |
| [NAV.md](docs/NAV.md) | Full navigation index |
| [ABOUT.md](docs/ABOUT.md) | Reality Await Layer (RAL) |
| [OPS_RUNBOOK.md](docs/OPS_RUNBOOK.md) | Operations + incident playbooks |
| [STABILITY.md](STABILITY.md) | Versioning policy + stability guarantees |
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
