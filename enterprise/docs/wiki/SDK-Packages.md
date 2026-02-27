# SDK Packages

Three standalone pip-installable packages for integrating governance into existing agent frameworks. Each package wraps `AgentSession` to produce sealed decision episodes without modifying application code.

## Package Overview

| Package | PyPI | Framework | Tests |
| --- | --- | --- | --- |
| `langchain-deepsigma` | `pip install langchain-deepsigma` | LangChain + LangGraph | 21 |
| `deepsigma-middleware` | `pip install deepsigma-middleware` | FastAPI + Flask | 15 |
| `openai-deepsigma` | `pip install openai-deepsigma` | Any tool-calling agent SDK | 11 |

Source: `packages/` directory in repo root.

---

## langchain-deepsigma

Repackages enterprise LangChain adapters into a standalone package with optional `AgentSession` integration.

### Exports

- **ExhaustCallbackHandler** — captures LLM calls, tool invocations, chain completions, and errors as exhaust events
- **GovernanceCallbackHandler** — enforces DTE constraints mid-chain with three violation modes (`raise`, `log`, `degrade`)
- **DTEViolationError** — raised when governance constraints are violated in `raise` mode
- **LangGraphExhaustTracker** — async event tracker for `astream_events()` output
- **LangGraphConnector** — trace-to-canonical record mapper with `to_agent_session_decisions()` for simplified decision dicts

### Usage

```python
from langchain_deepsigma import ExhaustCallbackHandler, GovernanceCallbackHandler
from core.agent import AgentSession

session = AgentSession("my-agent")
exhaust = ExhaustCallbackHandler(session=session)
governance = GovernanceCallbackHandler(dte_enforcer=my_dte, session=session)

chain.invoke(input, config={"callbacks": [exhaust, governance]})
```

---

## deepsigma-middleware

Generic REST middleware backed by `AgentSession` via `contextvars` for async safety.

### Exports

- **configure(agent_id, storage_dir)** — set default session parameters
- **log_decision(actor_type, decision_type)** — decorator for sync and async functions
- **get_session()** — returns or creates an `AgentSession` from the current context
- **DeepSigmaMiddleware** — ASGI middleware for FastAPI/Starlette
- **FlaskDeepSigma** — Flask extension

### FastAPI

```python
from deepsigma_middleware import DeepSigmaMiddleware

app = FastAPI()
app.add_middleware(DeepSigmaMiddleware, agent_id="api-server")
```

### Flask

```python
from deepsigma_middleware import FlaskDeepSigma

app = Flask(__name__)
FlaskDeepSigma(app, agent_id="api-server")
```

### Decorator

```python
from deepsigma_middleware import configure, log_decision

configure(agent_id="my-agent")

@log_decision(actor_type="api", decision_type="order_approval")
def approve_order(order_id):
    ...
```

---

## openai-deepsigma

Generic wrapper for tool-calling agent SDKs. Not vendor-specific at runtime.

### Exports

- **DeepSigmaAgentWrapper(agent, session, detect_drift=False)** — wraps any agent with a `.run()` method
- **AgentRunResult(output, episode_count, drift_signals, raw_result)** — structured result

### Usage

```python
from openai_deepsigma import DeepSigmaAgentWrapper
from core.agent import AgentSession

session = AgentSession("fraud-detector")
wrapper = DeepSigmaAgentWrapper(agent, session, detect_drift=True)

result = wrapper.run("Analyze transaction 12345")
print(result.episode_count)    # sealed episodes logged
print(result.drift_signals)    # drift detected across runs
```

### Lifecycle

1. Log intent decision (pre-run)
2. Execute `agent.run(input_text)`
3. Intercept each tool call and log as separate decision
4. Seal completion episode
5. If `detect_drift=True` and run count > 1: run `session.detect_drift()`

---

## CI / Publishing

Each package has a dedicated publish workflow triggered by version tags:

| Package | Tag Pattern | Workflow |
| --- | --- | --- |
| `langchain-deepsigma` | `langchain-v*` | `publish-langchain.yml` |
| `deepsigma-middleware` | `middleware-v*` | `publish-middleware.yml` |
| `openai-deepsigma` | `openai-v*` | `publish-openai.yml` |

All workflows use OIDC trusted publishing and test across Python 3.10-3.12.
