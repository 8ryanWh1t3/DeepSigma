# LangChain Governance Flow

Sequence diagram showing DTE enforcement via `GovernanceCallbackHandler` during a LangChain chain execution.

```mermaid
sequenceDiagram
    participant User
    participant Chain as LangChain Chain
    participant GCB as GovernanceCallbackHandler
    participant DTE as DTE Engine
    participant LLM as LLM Provider
    participant Tool as Tool
    participant Exhaust as Exhaust Inbox

    User->>Chain: invoke(input)

    Note over Chain,GCB: on_llm_start
    Chain->>GCB: on_llm_start(model, prompt)
    GCB->>DTE: check(token_budget, TTL, model_allowlist)

    alt DTE passes
        DTE-->>GCB: OK
        GCB-->>Chain: proceed
        Chain->>LLM: call(prompt)
        LLM-->>Chain: response

        Note over Chain,GCB: on_llm_end
        Chain->>GCB: on_llm_end(tokens_used)
        GCB->>DTE: debit(tokens_used)
    else DTE violation
        DTE-->>GCB: VIOLATION (field, actual, limit)
        alt mode = raise
            GCB-->>Chain: raise DTEViolationError
            Chain-->>User: DTEViolationError
        else mode = log
            GCB->>Exhaust: emit(warning_event)
            GCB-->>Chain: proceed (with warning)
            Chain->>LLM: call(prompt)
            LLM-->>Chain: response
        else mode = degrade
            GCB->>DTE: get_degrade_step()
            DTE-->>GCB: fallback_action
            GCB-->>Chain: substitute(fallback_action)
        end
    end

    Note over Chain,GCB: on_tool_start
    Chain->>GCB: on_tool_start(tool_name, input)
    GCB->>DTE: check(scope, cost_gate)
    DTE-->>GCB: OK
    GCB-->>Chain: proceed
    Chain->>Tool: execute(input)
    Tool-->>Chain: result

    Note over Chain,GCB: on_tool_end
    Chain->>GCB: on_tool_end(result)
    GCB->>DTE: verify(output_schema, latency)
    DTE-->>GCB: OK
    GCB->>Exhaust: emit(episode_event)

    Chain-->>User: final result
```

## Key Details

- **Every LLM and tool call** passes through the governance callback before execution.
- **Violation decision tree**: The handler checks `violation_mode` to determine whether to raise, log, or degrade.
- **Degrade path**: Consults the Degrade Ladder for the next safe fallback action.
- **Exhaust events** are emitted on every tool completion and on every violation, regardless of mode.
