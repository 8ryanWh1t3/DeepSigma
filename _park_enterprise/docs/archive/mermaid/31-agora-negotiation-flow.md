# Agora Negotiation Flow — Unknown Protocol → Sealed Contract → Runtime

How two parties with incompatible protocols converge on a shared contract through LLM-assisted negotiation, then execute without further LLM calls.

```mermaid
flowchart TB
    START([Unknown Protocol Encountered]) --> PROBE

    subgraph NEGOTIATE [Negotiation Phase — LLM-assisted]
        PROBE[Probe: Exchange capability descriptors] --> MATCH{Known protocol<br/>match?}
        MATCH -- Yes --> ADAPTER[Select existing adapter<br/>MCP / A2A / AG-UI]
        MATCH -- No --> GEN[LLM generates<br/>ProtocolContract draft]
        GEN --> REVIEW{Both parties<br/>accept?}
        REVIEW -- No --> COUNTER[Counter-propose<br/>constraints / fields]
        COUNTER --> GEN
        REVIEW -- Yes --> SEAL
    end

    ADAPTER --> SEAL
    SEAL[Seal contract<br/>contract_id + version + hash] --> COMPILE

    subgraph RUNTIME [Runtime Phase — No LLM]
        COMPILE[Compile contract → executable routine] --> CACHE[Cache routine<br/>keyed by contract_id]
        CACHE --> EXEC[Execute routine on each call]
        EXEC --> MONITOR[Monitor for drift signals]
    end

    MONITOR --> DRIFT{Drift<br/>detected?}
    DRIFT -- No --> EXEC
    DRIFT -- Yes --> CLASSIFY

    subgraph PATCH [Drift → Patch Loop]
        CLASSIFY[Classify drift type<br/>schema / semantic / capability / policy] --> SEVERITY{Severity?}
        SEVERITY -- Low --> AUTO[Auto-patch:<br/>retry with backoff]
        SEVERITY -- Medium --> RENEG[Re-negotiate<br/>new contract version]
        SEVERITY -- High/Critical --> HUMAN[Require human approval]
        AUTO --> SEAL2[Seal patch as DLR]
        RENEG --> GEN
        HUMAN --> APPROVE{Approved?}
        APPROVE -- Yes --> RENEG
        APPROVE -- No --> BLOCK([Block + escalate])
    end

    SEAL2 --> EXEC
```
