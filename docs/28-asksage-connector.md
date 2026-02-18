# AskSage Connector

AskSage API connector for FedRAMP-authorized LLM queries, training, and model management.

The `AskSageConnector` provides query, model listing, dataset management, and training capabilities via the AskSage REST API. Supports persona selection, file-based queries, and prompt history retrieval.

**Source:** `adapters/asksage/connector.py`

---

## Setup

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ASKSAGE_EMAIL` | Yes | -- | AskSage account email |
| `ASKSAGE_API_KEY` | Yes | -- | AskSage API key |
| `ASKSAGE_BASE_URL` | No | `https://api.asksage.ai` | AskSage API base URL |

```bash
export ASKSAGE_EMAIL="user@example.com"
export ASKSAGE_API_KEY="your-api-key"
```

No additional Python dependencies required.

---

## Usage

### Basic query

```python
from adapters.asksage.connector import AskSageConnector

connector = AskSageConnector()
result = connector.query("What is the NIST CSF?")
print(result)
```

### Query with model and dataset

```python
result = connector.query(
    prompt="Summarize the latest FISMA requirements",
    model="gpt-4",
    dataset="nist-docs",
    persona="security-analyst",
)
```

### Query with file attachment

```python
result = connector.query_with_file(
    prompt="Analyze this document",
    file_path="/path/to/document.pdf",
    model="gpt-4",
)
```

### List available models

```python
models = connector.get_models()
for m in models:
    print(m)
```

### Train on content

```python
result = connector.train(
    content="DeepSigma enforces DTE constraints at runtime...",
    dataset="deepsigma-docs",
)
```

---

## API Reference

### `AskSageConnector`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `email` | `str` | `ASKSAGE_EMAIL` env | AskSage account email. |
| `api_key` | `str` | `ASKSAGE_API_KEY` env | AskSage API key. |
| `base_url` | `str` | `ASKSAGE_BASE_URL` env | API base URL. |

### Methods

| Method | Returns | Description |
|---|---|---|
| `get_token()` | `str` | Acquire or return cached 24h access token. |
| `query(prompt, model?, dataset?, persona?)` | `dict` | Send a query and return the response. |
| `query_with_file(prompt, file_path, model?)` | `dict` | Query with a file attachment. |
| `get_models()` | `list[dict]` | List available models. |
| `get_datasets()` | `list[dict]` | List user datasets. |
| `get_personas()` | `list[dict]` | List available personas. |
| `get_user_logs(limit=20)` | `list[dict]` | Get prompt history. |
| `train(content, dataset)` | `dict` | Train on content into a dataset. |

### Authentication

The connector acquires a 24-hour access token via `/user/get-token-with-api-key` using the configured email and API key. Tokens are cached in memory and refreshed automatically after 23 hours.

The token is sent as `x-access-tokens` header on all subsequent requests.

---

## Exhaust Adapter

AskSage query results can be captured as exhaust events for the DeepSigma pipeline:

```python
from adapters.asksage.connector import AskSageConnector
from adapters.langgraph_exhaust import LangGraphExhaustTracker

connector = AskSageConnector()
result = connector.query("What is NIST 800-53?")

# Wrap as exhaust event
event = {
    "event_type": "tool_end",
    "name": "asksage_query",
    "data": result,
}
```

---

## MCP Tools

| Tool | Description |
|---|---|
| `asksage_query` | Send a prompt to AskSage with optional model/dataset/persona |
| `asksage_models` | List available AskSage models |
| `asksage_datasets` | List user datasets |
| `asksage_train` | Train content into a named dataset |

---

## Files

| File | Path |
|---|---|
| Source | `adapters/asksage/connector.py` |
| This doc | `docs/28-asksage-connector.md` |
