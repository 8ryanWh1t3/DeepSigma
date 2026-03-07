# Model Exchange Engine (MEE)

> Deep Sigma is the reactor, boundary, and memory system.
> Models are interchangeable cognitive thrusters.
> Models produce exhaust. Deep Sigma produces judgment.

## Overview

The Model Exchange Engine standardises how external or local models plug into Deep Sigma.  Models can draft, reason, summarise, and disagree — but they **cannot** commit canon, approve themselves, bypass AuthorityOps, or overwrite memory.

MEE output is **draft-grade reasoning**.  Any patch / apply / canon operation must go through existing AuthorityOps / feeds / decision surface flow.  MEE can recommend escalation only.

## Architecture

```
┌──────────────────────────────────────────────┐
│               ModelExchangeEngine            │
│  ┌──────────┐  ┌────────┐  ┌──────────────┐ │
│  │ Registry │→ │ Router │→ │  Evaluator   │ │
│  └──────────┘  └────────┘  └──────────────┘ │
│       ↑                          ↓           │
│  ┌─────────┐              ┌────────────┐     │
│  │Adapters │              │Evaluation  │     │
│  │ apex    │              │  Result    │     │
│  │ mock    │              └────────────┘     │
│  │ openai  │                    ↓            │
│  │ claude  │          ┌────────────────┐     │
│  │ gguf    │          │  Escalation    │     │
│  └─────────┘          │  Recommendation│     │
│                       └────────────────┘     │
└──────────────────────────────────────────────┘
          ↓ (draft only)
   AuthorityOps / DecisionSurface / FEEDS
```

## Adapters

| Adapter | Provider | Mode | Description |
|---------|----------|------|-------------|
| `apex` | local | mock / command | Cognis-APEX-3.2 via llama.cpp |
| `mock` | local | mock | Deterministic output for tests |
| `openai` | openai | mock / live | GPT-4o via API |
| `claude` | anthropic | mock / live | Claude via Anthropic API |
| `gguf` | local | mock / command | Any GGUF model via local runtime |

## Authority Boundary

MEE enforces these rules:

1. MEE output is draft-grade reasoning
2. Any patch/apply/canon operation must go through AuthorityOps
3. MEE can recommend escalation only
4. MEE cannot approve itself
5. No adapter can directly patch/apply/commit canon
