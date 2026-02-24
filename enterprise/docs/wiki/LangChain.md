# LangChain

Integration pattern:
- wrap tools with RAL governance
- capture spans/telemetry via callback handler
- stamp episodes automatically

Goal:
**Every tool/action call becomes budgeted, TTL-gated, verifiable, sealable.**

## Governance Adapter

The **GovernanceCallbackHandler** enforces DTE constraints mid-chain. It intercepts `on_llm_start`, `on_tool_start`, and `on_tool_end` callbacks to check budget, TTL, scope, and model allowlists before execution proceeds.

Three violation modes:
- **raise** -- abort with `DTEViolationError`
- **log** -- emit a warning and continue
- **degrade** -- trigger the Degrade Ladder for a safer fallback

Composes cleanly with `ExhaustCallbackHandler` -- pass both in the callback list.

See [LangChain Governance](LangChain-Governance.md) for full API reference, configuration, and comparison with the LangGraph DTETracker.
