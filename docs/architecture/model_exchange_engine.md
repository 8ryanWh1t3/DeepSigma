# Model Exchange Engine (MEE)

> Deep Sigma is the reactor, boundary, and memory system.
> Models are interchangeable cognitive thrusters.
> Models produce exhaust. Deep Sigma produces judgment.

## What MEE Is

The Model Exchange Engine (MEE) is a first-class architectural capability that standardises how external or local models plug into Deep Sigma.  It provides:

- **Adapter registry** — register and discover model adapters
- **Packet routing** — dispatch reasoning packets to one or many adapters
- **Consensus scoring** — measure agreement across adapter outputs
- **Contradiction detection** — conservative heuristic-based conflict detection
- **Evidence coverage** — track how well claims are grounded in evidence
- **Evaluation** — aggregate results into a single `EvaluationResult` with escalation recommendation
- **Authority boundary** — enforce that MEE output is draft-only

## Why Deep Sigma Stays Model-Agnostic

Deep Sigma governs five fundamental concerns: **Truth, Reasoning, Memory, Drift, and Authority**.  These concerns are model-independent — they apply regardless of which model produces the reasoning.

Models are interchangeable **cognitive thrusters**.  They can:
- Draft claims
- Produce reasoning chains
- Summarise evidence
- Disagree with each other

Models **cannot**:
- Commit canon
- Approve themselves
- Bypass AuthorityOps
- Overwrite memory
- Directly patch or apply changes

## Cognitive Thruster Concept

Each model adapter is a "cognitive thruster" — a pluggable reasoning engine that produces structured output.  The MEE evaluates this output, detects contradictions, measures consensus, and recommends an escalation level.

```
                     ┌─────────────────┐
                     │   Packet Input  │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Registry     │
                     └────────┬────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │   APEX    │  │   Mock    │  │  Claude   │  ...
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                     ┌────────▼────────┐
                     │   Evaluator    │
                     │  ┌───────────┐ │
                     │  │ Consensus │ │
                     │  │ Contradict│ │
                     │  │ Confidence│ │
                     │  └───────────┘ │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │ EvaluationResult│
                     │  (draft-only)   │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │ AuthorityOps /  │
                     │ DecisionSurface │
                     └─────────────────┘
```

## APEX — First Cognitive Thruster

APEX (Cognis-APEX-3.2) is the first adapter, demonstrating the pattern:

| Property | Value |
|----------|-------|
| Provider | local |
| Model | Cognis-APEX-3.2 |
| Runtime | llama.cpp (command) / in-process (mock) |
| Modes | mock (default), command |

**Mock mode** returns deterministic structured output — no runtime or network required.
**Command mode** shells out to a configured local runtime, parses structured JSON output, and wraps it in a `ReasoningResult`.

## Available Adapters

| Adapter | Provider | Default Mode | Description |
|---------|----------|-------------|-------------|
| `apex` | local | mock | Cognis-APEX-3.2 via llama.cpp |
| `mock` | local | mock | Deterministic test adapter |
| `openai` | openai | mock | GPT-4o via OpenAI API |
| `claude` | anthropic | mock | Claude via Anthropic Messages API |
| `gguf` | local | mock | Any GGUF model via local runtime |

## MEE Is Drafting-Only

MEE output is **draft-grade reasoning**.  The escalation policy:

| Condition | Escalation |
|-----------|-----------|
| High contradiction (≥0.5) or low evidence (<0.3) | `authority-review` |
| Medium disagreement (<0.5 agreement) or moderate contradiction (≥0.2) | `human-review` |
| Strong agreement, model-produced | `accept-for-drafting` |
| No claims / malformed output | `reject` |

## How MEE Interacts with AuthorityOps

1. MEE produces an `EvaluationResult` with an escalation recommendation
2. The calling system (CLI, API, pipeline) decides whether to:
   - Accept the draft for further processing
   - Route to human review
   - Escalate to AuthorityOps for authority-level review
   - Reject the output entirely
3. Any canon/commit/patch operation goes through existing AuthorityOps, FEEDS, or DecisionSurface flows
4. MEE **never** writes directly to canonical stores

## Future Adapters

Planned adapters beyond the initial five:

- **Mission-specific fine-tuned models** — domain-adapted GGUF models
- **Ensemble adapters** — adapters that internally run multiple models
- **Retrieval-augmented adapters** — adapters that query vector stores before reasoning

## Data Contracts

- `ReasoningResult` — single adapter output (see `model_exchange_result.schema.json`)
- `EvaluationResult` — aggregated evaluation (see `model_exchange_evaluation.schema.json`)
- `CandidateClaim` — a single model-produced claim
- `ReasoningStep` — a step in the reasoning chain
- `ContradictionRecord` — a detected contradiction
- `ModelMeta` — metadata about the model that produced the result

## Usage

```python
from core.model_exchange import ModelExchangeEngine
from core.model_exchange.adapters import ApexAdapter, MockAdapter

engine = ModelExchangeEngine()
engine.registry.register("apex", ApexAdapter())
engine.registry.register("mock", MockAdapter())

packet = {
    "request_id": "REQ-001",
    "question": "Is the system within SLA?",
    "evidence": ["ev-latency", "ev-errors"],
}

evaluation = engine.run(packet, ["apex", "mock"])
print(evaluation.recommended_escalation)  # "accept-for-drafting"
```

## CLI

```bash
python -m core.cli mee demo          # Run demo with all adapters
python -m core.cli mee demo --json   # JSON output
python -m core.cli mee health        # Check adapter health
```
