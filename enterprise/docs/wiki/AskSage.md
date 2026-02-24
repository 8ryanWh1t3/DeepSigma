# AskSage

Integration with [AskSage](https://asksage.ai) for DoD/IC-grade LLM query, training, and dataset management.

## Overview

AskSage provides a multi-model gateway with IL5/IL6 compliance. The RAL adapter wraps every AskSage API call in DTE-gated, budget-tracked episodes and routes exhaust through the standard Exhaust Inbox pipeline.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/query` | POST | Submit a prompt to a selected model |
| `/models` | GET | List available models and capabilities |
| `/datasets` | GET/POST | List or upload training datasets |
| `/train` | POST | Launch a fine-tuning job on a dataset |
| `/history` | GET | Retrieve past query results |

## Auth Pattern

AskSage uses a **two-phase auth flow**:

1. **API Key** -- long-lived secret stored in env `ASKSAGE_API_KEY`
2. **Session Token** -- 24-hour bearer token obtained via `/auth/token`

```python
from deepsigma.adapters.asksage import AskSageClient

client = AskSageClient(
    api_key=os.environ["ASKSAGE_API_KEY"],
    # token auto-refreshes every 24h
)
```

The adapter handles token refresh transparently. If the token expires mid-episode, the adapter re-authenticates and retries once before raising `AskSageAuthError`.

## Query Flow

```
User prompt
  --> AskSageClient.query(model, prompt, dte)
    --> DTE budget check (tokens, cost, TTL)
    --> POST /query {model, prompt, token}
    --> Response
    --> ExhaustAdapter.emit(EpisodeEvent)
    --> Canonical record sealed
```

## Exhaust Adapter

Every query, training job, and dataset operation emits an `EpisodeEvent`:

```python
from deepsigma.exhaust import ExhaustAdapter

adapter = ExhaustAdapter(source="asksage")
adapter.emit(event)  # routed to Exhaust Inbox
```

Fields captured: `model`, `prompt_hash`, `token_count`, `latency_ms`, `cost_usd`, `dte_id`, `episode_id`.

## MCP Tools

The adapter registers four MCP tools:

| Tool | Description |
|------|-------------|
| `asksage.query` | Submit a governed prompt to AskSage |
| `asksage.models` | List available models |
| `asksage.datasets` | List or upload datasets |
| `asksage.history` | Retrieve query history for an episode |

### Example: MCP query call

```json
{
  "tool": "asksage.query",
  "arguments": {
    "model": "gpt-4o",
    "prompt": "Summarize the latest threat brief",
    "dte_id": "dte-abc-123",
    "max_tokens": 2048
  }
}
```

## Configuration

```yaml
# config/asksage.yaml
asksage:
  base_url: https://api.asksage.ai/v1
  api_key_env: ASKSAGE_API_KEY
  token_ttl_hours: 24
  default_model: gpt-4o
  exhaust:
    adapter: asksage
    emit_prompts: false   # hash-only by default
```

## Related

- [Integrations](Integrations.md)
- [MCP](MCP.md)
- [Exhaust Inbox](Exhaust-Inbox.md)
- [Snowflake](Snowflake.md)
