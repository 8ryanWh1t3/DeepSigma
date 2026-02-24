# Local Inference Adapter

Run LLM-based knowledge extraction on any OpenAI-compatible local server — llama.cpp, Ollama, vLLM, LocalAI, text-gen-webui, and more. No cloud API keys required.

**Source:** `adapters/local_llm/connector.py`, `adapters/local_llm/exhaust.py`

---

## Why Local Inference?

- **Airgapped / sovereign deployments** — no data leaves your network
- **Cost control** — zero per-token API costs after hardware investment
- **Low latency** — GPU on the same machine or LAN
- **Development** — iterate on extraction prompts without burning API credits

## Setup

### 1. Install the local extras

```bash
pip install -e ".[local]"
```

This adds `httpx` for HTTP communication with the local server.

### 2. Start a local server

Any server implementing OpenAI-compatible `/v1/chat/completions` and `/v1/models` endpoints works. Examples:

```bash
# llama.cpp server
./llama-server -m models/llama-3-8b.Q4_K_M.gguf --port 8080

# Ollama
ollama serve  # default port 11434
# then: ollama run llama3

# vLLM
python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3-8B
```

### 3. Configure environment

```bash
export DEEPSIGMA_LLM_BACKEND=local
export DEEPSIGMA_LOCAL_BASE_URL=http://localhost:8080
export EXHAUST_USE_LLM=1
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `DEEPSIGMA_LLM_BACKEND` | `anthropic` | Set to `local` to use local inference |
| `DEEPSIGMA_LOCAL_BASE_URL` | `http://localhost:8080` | Server URL |
| `DEEPSIGMA_LOCAL_API_KEY` | *(empty)* | Bearer token if server requires auth |
| `DEEPSIGMA_LOCAL_MODEL` | *(empty)* | Model name to send in requests; empty = server default |
| `DEEPSIGMA_LOCAL_TIMEOUT` | `120` | HTTP timeout in seconds |
| `EXHAUST_USE_LLM` | `0` | Master on/off switch for LLM extraction (shared with Anthropic backend) |

---

## Usage

### Direct connector usage

```python
from adapters.local_llm import LlamaCppConnector

connector = LlamaCppConnector()

# Health check
print(connector.health())
# {"ok": True, "models": ["llama-3-8b"], "base_url": "http://localhost:8080"}

# Chat completion
result = connector.chat([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Summarize the decision."},
])
print(result["text"])

# Text completion
result = connector.generate("Complete this sentence:", max_tokens=100)
print(result["text"])
```

### Exhaust pipeline (automatic)

When `DEEPSIGMA_LLM_BACKEND=local` and `EXHAUST_USE_LLM=1`, the exhaust refiner automatically routes LLM extraction through the local server:

```bash
DEEPSIGMA_LLM_BACKEND=local EXHAUST_USE_LLM=1 \
  python -m core score ./episodes.json --json
```

No code changes required — the `LLMExtractor` detects the backend and dispatches accordingly.

### Exhaust adapter (manual event emission)

```python
from adapters.local_llm import LlamaCppConnector
from adapters.local_llm.exhaust import LocalLLMExhaustAdapter

connector = LlamaCppConnector()
adapter = LocalLLMExhaustAdapter(connector, project="my-project")

# Chat with automatic exhaust event emission
result = adapter.chat_with_exhaust([
    {"role": "user", "content": "What are the key risks?"},
])
# Emits: prompt, response, metric events to exhaust endpoint
```

---

## Tested Servers

| Server | Tested | Notes |
|---|---|---|
| llama.cpp (`llama-server`) | Yes | Reference implementation |
| Ollama | Yes | Use `DEEPSIGMA_LOCAL_BASE_URL=http://localhost:11434` |
| vLLM | Yes | OpenAI-compatible mode |
| LocalAI | Yes | Drop-in OpenAI replacement |
| text-generation-webui | Yes | Enable `--api` flag |

## Model Recommendations

For knowledge extraction (truth/reasoning/memory), models with strong instruction-following work best:

- **Llama 3 8B** (Q4_K_M or higher) — good balance of speed and quality
- **Mistral 7B Instruct** — strong extraction quality
- **Phi-3 Mini** — lightweight, fast, decent extraction

Larger models (13B+, 70B) produce higher-quality extractions but require more VRAM/RAM.

---

## Backward Compatibility

- Default backend is `anthropic` — zero changes to existing deployments
- `EXHAUST_USE_LLM=1` remains the master on/off switch
- `ANTHROPIC_API_KEY` is only required when `DEEPSIGMA_LLM_BACKEND=anthropic` (default)
- All existing tests pass unmodified
