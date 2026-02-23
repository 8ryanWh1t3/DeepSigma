# Σ OVERWATCH — Integration Cookbook

Runnable, verifiable examples for each adapter. Every recipe includes prerequisites, steps, expected output, verification, and failure modes.

---

## Quick Chooser

| If you want to… | Use this recipe |
|-----------------|----------------|
| Connect an MCP client to OVERWATCH governance | [MCP: Hello DeepSigma](mcp/hello_deepsigma/README.md) |
| Enforce pre/post action contracts on decisions | [OpenClaw: Supervised Run](openclaw/supervised_run/README.md) |
| Emit decision spans to Jaeger / Honeycomb / Tempo | [OTel: Trace Drift Patch](otel/trace_drift_patch/README.md) |

---

## Common Prerequisites

All recipes assume:

```bash
# 1. Clone and enter the repo
git clone https://github.com/8ryanWh1t3/DeepSigma.git && cd DeepSigma

# 2. Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install the package and dev deps
pip install -r requirements.txt && pip install -e .
```

**Python version required:** 3.10+

```bash
python --version   # Must show 3.10 or higher
```

---

## Verification Concept

Each recipe produces one or more of:
- A JSON artifact (DLR entry, drift event, sealed episode)
- A console output matching an expected pattern
- A test assertion that passes

Recipes explicitly show what "success" looks like and what the most common failure modes are.

---

## Adapters Overview

| Adapter | Path | Status |
|---------|------|--------|
| MCP | `adapters/mcp/` | Scaffold — JSON-RPC stdio loopback |
| OpenClaw | `adapters/openclaw/` | Alpha — contract verification |
| OpenTelemetry | `adapters/otel/` | Alpha — span export |

> **MCP note:** The MCP adapter is a scaffold demonstrating the intended contract. It implements the JSON-RPC protocol over stdio and is ready for integration with a real MCP host.
