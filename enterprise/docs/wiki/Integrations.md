# Integrations

RAL is designed to be **tooling-agnostic**.

Primary targets:

- [MCP](MCP.md)
- [LangChain](LangChain.md) (+ [Governance Adapter](LangChain-Governance.md))
- [AskSage](AskSage.md)
- [Snowflake](Snowflake.md)
- [Palantir Foundry](Palantir-Foundry.md)
- [Power Platform](Power-Platform.md)
- [OpenTelemetry](OpenTelemetry.md)

## SDK Packages

Three standalone pip packages for drop-in framework integration. See [SDK Packages](SDK-Packages.md) for full docs.

| Package | Install | What it does |
| --- | --- | --- |
| `langchain-deepsigma` | `pip install langchain-deepsigma` | LangChain + LangGraph exhaust and governance callbacks |
| `deepsigma-middleware` | `pip install deepsigma-middleware` | `@log_decision` decorator, ASGI middleware, Flask extension |
| `openai-deepsigma` | `pip install openai-deepsigma` | Generic agent wrapper — intent, tool calls, drift detection |

## Connector Summary

| Connector | Transport | MCP Tools | Auth | Exhaust |
| --- | --- | --- | --- | --- |
| MCP | JSON-RPC stdio | 7 | N/A (local) | Built-in |
| LangChain | Python callbacks | -- | N/A (in-process) | ExhaustCallbackHandler |
| AskSage | HTTPS REST | 4 | API Key + 24h Token | asksage adapter |
| Snowflake | HTTPS REST + SQL | 5 | JWT / OAuth / PAT | snowflake adapter |
| Palantir Foundry | HTTPS REST | -- | OAuth | foundry adapter |
| Power Platform | Dataverse Web API | -- | OAuth / App Registration | power adapter |
| OpenTelemetry | gRPC / HTTP | -- | N/A | OTLP exporter |

## FEEDS Event Bus

Internal event-driven integration layer connecting governance primitives. FEEDS is not an external connector — it connects TS, ALS, DLR, DS, and CE via file-based pub/sub with manifest-first ingest, authority validation, and canon versioning. See the Home page for the 5-stage pipeline overview.
