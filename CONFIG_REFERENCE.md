# Σ OVERWATCH — Configuration Reference

**Audience:** Operators, integrators
**Version:** v0.3.2
**See also:** [OPS_RUNBOOK.md](OPS_RUNBOOK.md) · [STABILITY.md](STABILITY.md)

---

## Overview

DeepSigma v0.3.x has minimal configuration surface by design. The system is stdlib-first and file-driven. There are three configuration surfaces:

1. **CLI arguments** — passed directly to `python -m coherence_ops ...` commands
2. **Policy pack files** — YAML/JSON documents loaded at runtime by the supervisor
3. **Environment variables** — used by the OpenTelemetry adapter and optional integrations

There are no global config files (no `settings.yaml`, no `.env` required for core operation).

---

## 1. CLI Arguments

### `coherence_ops` CLI

**Entry point:** `python -m coherence_ops <subcommand>` or `coherence <subcommand>` (after `pip install -e .`)

#### `score`

```
python -m coherence_ops score <episodes_path> [--json]
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `episodes_path` | path | yes | Path to JSON file containing one episode or a list of episodes |
| `--json` | flag | no | Output raw JSON instead of human-readable report |

**What it changes:** Output format only. No behavior difference.

**Example:**
```bash
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json --json
```

---

#### `audit`

```
python -m coherence_ops audit <episodes_path>
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `episodes_path` | path | yes | Path to JSON file with episodes |

**Example:**
```bash
python -m coherence_ops audit ./coherence_ops/examples/sample_episodes.json
```

---

#### `mg export`

```
python -m coherence_ops mg export <episodes_path> --format=<fmt> [--output=<path>]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `episodes_path` | path | — | Source episode file |
| `--format` | `json` \| `graphml` \| `neo4j` | `json` | Export format |
| `--output` | path | stdout | Write to file instead of stdout |

**Example:**
```bash
python -m coherence_ops mg export ./coherence_ops/examples/sample_episodes.json \
    --format=graphml --output=/tmp/mg.graphml
```

---

#### `iris query`

```
python -m coherence_ops iris query --type <TYPE> [--target <id>] [--json]
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--type` | `WHY` \| `WHAT_CHANGED` \| `WHAT_DRIFTED` \| `RECALL` \| `STATUS` | yes | Query type |
| `--target` | string | no | Episode ID to query against (for WHY, WHAT_CHANGED) |
| `--json` | flag | no | Output raw JSON |

**What changes behavior:** `--type` selects the query strategy. `--target` narrows results to a specific episode.

**Example:**
```bash
python -m coherence_ops iris query --type WHY --target ep-001
python -m coherence_ops iris query --type WHAT_DRIFTED --json
```

---

#### `demo`

```
python -m coherence_ops demo <episodes_path>
```

Runs `score` + IRIS STATUS query in one pass.

---

## 2. Policy Pack Files

Policy packs are YAML or JSON files loaded by the `OpenClawSupervisor`. They define contracts (pre/post conditions) for each `decisionType`.

### Minimal Safe Config

```yaml
# policy_pack_min.yaml — minimal working policy pack
version: "1.0"
policyPackId: "min-001"
name: "Minimal Policy Pack"
contracts: {}   # No contracts — all actions pass precondition checks
```

### Full Structure

```yaml
version: "1.0"
policyPackId: "pp-prod-001"
name: "Production Policy Pack"
contracts:
  LoanApproval:
    contractId: "contract-loan-001"
    preconditions:
      - field: "applicant_verified"
        equals: true
        message: "Applicant must be verified before loan approval"
      - field: "amount_requested"
        equals: null   # null means field must be absent
    postconditions:
      - field: "decision"
        equals: "approved"
        message: "Decision must be explicitly 'approved'"
  TradeExecution:
    contractId: "contract-trade-001"
    preconditions:
      - field: "market_open"
        equals: true
```

### Loading a Policy Pack

```python
import yaml
from adapters.openclaw.adapter import OpenClawSupervisor

policy = yaml.safe_load(open("policy_pack_min.yaml"))
supervisor = OpenClawSupervisor(policy_pack=policy)
```

### Where Policy Packs Live

Default example packs are in `policy_packs/`. You can place your own anywhere — just pass the path when loading.

---

## 3. Environment Variables

### OpenTelemetry Adapter

The OTel adapter (`adapters/otel/exporter.py`) uses standard OpenTelemetry SDK environment variables. None are required — without them, the adapter defaults to console output.

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_SERVICE_NAME` | `"sigma-overwatch"` | Service name shown in traces |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | *(none — console only)* | gRPC endpoint for OTLP export (e.g., `http://localhost:4317`) |
| `OTEL_EXPORTER_OTLP_HEADERS` | *(none)* | Auth headers for managed OTEL services (e.g., Honeycomb API key) |
| `OTEL_SDK_DISABLED` | `"false"` | Set to `"true"` to disable all tracing silently |

**Safe minimal config (console traces only):**
```bash
export OTEL_SERVICE_NAME="sigma-overwatch"
# No OTLP endpoint — spans print to stdout
```

**Remote OTLP config:**
```bash
export OTEL_SERVICE_NAME="sigma-overwatch"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
```

---

### Dashboard API Server

The dashboard API server (`dashboard/api_server.py`) uses no environment variables. It always binds to `0.0.0.0:8000`. The React dashboard expects the API at `http://localhost:8000`.

---

### Optional / Future Integrations

| Variable | Used By | Status |
|----------|---------|--------|
| `ANTHROPIC_API_KEY` | LangChain cookbook examples | Optional — only for LLM-driven demos |
| `DEEPSIGMA_CORPUS_PATH` | Not implemented yet | Reserved for future corpus config |

---

## 4. What Changes Behavior vs. What Changes Observability

| Config | Changes Behavior | Changes Observability |
|--------|-----------------|----------------------|
| `--json` flag | No | Yes — output format only |
| `--format` (mg export) | No | Yes — export format only |
| `--target` (iris) | Yes — narrows result set | — |
| `--type` (iris) | Yes — selects query strategy | — |
| Policy pack `contracts` | Yes — can block actions | — |
| `OTEL_*` env vars | No | Yes — trace destination |
| `OTEL_SDK_DISABLED=true` | No | Yes — disables traces |

---

## 5. Defaults Summary ("Safe Minimal Config")

To run DeepSigma with zero config:

```bash
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma
pip install -r requirements.txt
pip install -e .

# Run with no config — uses bundled sample data
python -m coherence_ops score ./coherence_ops/examples/sample_episodes.json
python -m coherence_ops.examples.drift_patch_cycle
```

No YAML file, no env vars, no database, no network. Everything defaults to in-memory operation with the bundled sample corpus.

---

*See also: [OPS_RUNBOOK.md](OPS_RUNBOOK.md) · [STABILITY.md](STABILITY.md) · [TEST_STRATEGY.md](TEST_STRATEGY.md)*
