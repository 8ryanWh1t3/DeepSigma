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

## Connector Summary

| Connector | Transport | MCP Tools | Auth | Exhaust |
|-----------|-----------|-----------|------|---------|
| MCP | JSON-RPC stdio | 7 | N/A (local) | Built-in |
| LangChain | Python callbacks | -- | N/A (in-process) | ExhaustCallbackHandler |
| AskSage | HTTPS REST | 4 | API Key + 24h Token | asksage adapter |
| Snowflake | HTTPS REST + SQL | 5 | JWT / OAuth / PAT | snowflake adapter |
| Palantir Foundry | HTTPS REST | -- | OAuth | foundry adapter |
| Power Platform | Dataverse Web API | -- | OAuth / App Registration | power adapter |
| OpenTelemetry | gRPC / HTTP | -- | N/A | OTLP exporter |
