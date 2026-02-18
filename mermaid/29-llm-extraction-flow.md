# LLM Extraction Flow

Internal mechanics of `LLMExtractor` — how an episode becomes structured TRUTH / REASONING / MEMORY buckets via the Anthropic Messages API, with full fallback handling.

```mermaid
flowchart LR
    EP[DecisionEpisode] --> BUILD["_build_prompt(episode)\n──────────────\nSerialise each event:\n  [event_type] timestamp source=... payload=...\nTruncate transcript at 6 000 chars\nAppend 'Extract knowledge:'"]

    BUILD --> CHK{len > 6000?}
    CHK -->|yes| TRUNC["transcript[:6000]\n+ '...(truncated)'"]
    CHK -->|no| CALL
    TRUNC --> CALL

    CALL["_call_api(prompt)\n──────────────\nanthropics.Anthropic(api_key=...)\n.messages.create(\n  model = claude-haiku-4-5-20251001\n  max_tokens = 2048\n  system = SYSTEM_PROMPT\n  messages = [{role:user, content:prompt}]\n)"]

    CALL -->|"message.content[0].text"| PARSE["_parse_response(text)\n──────────────\nStrip markdown fences if present\njson.loads(stripped)\nBuild TruthItem / ReasoningItem / MemoryItem\nClamp all confidence to [0.0, 1.0]"]

    PARSE --> MERGE["Merge with rule-based memory:\n• keep episode node from rule-based\n• add LLM memory items (non-episode)"]

    MERGE --> OUT["Buckets\n{truth, reasoning, memory}"]

    CALL -->|"any Exception"| FB["Fallback\nlogger.warning(...)\nreturn empty buckets"]
    PARSE -->|"json.JSONDecodeError\nor KeyError"| FB
    FB --> RB["Rule-based extraction\nruns transparently"]

    style EP fill:#1a1a2e,stroke:#e94560,color:#fff
    style OUT fill:#0f3460,stroke:#533483,color:#fff
    style FB fill:#e94560,stroke:#fff,color:#fff
    style RB fill:#16213e,stroke:#0f3460,color:#fff
```

## API Call Sequence

End-to-end from `refine_episode()` caller through Anthropic and back.

```mermaid
sequenceDiagram
    participant Caller as refine_episode()
    participant Check as Env Check
    participant LLM as LLMExtractor
    participant Build as _build_prompt()
    participant API as Anthropic Messages API
    participant Parse as _parse_response()
    participant Rule as Rule-Based Extractor

    Caller->>Check: use_llm=True?
    alt ANTHROPIC_API_KEY not set
        Check-->>Caller: skip LLM path
        Caller->>Rule: extract_truth/reasoning/memory()
        Rule-->>Caller: buckets
    else key is set
        Check->>LLM: LLMExtractor().extract(episode)
        LLM->>Build: episode events
        Build-->>LLM: prompt string (≤6000 chars)
        LLM->>API: messages.create(model, system, user=prompt)
        alt API success
            API-->>LLM: message.content[0].text (JSON)
            LLM->>Parse: raw text
            Parse-->>LLM: {truth[], reasoning[], memory[]}
            LLM->>LLM: merge episode node from rule-based
            LLM-->>Caller: merged buckets
        else API error or bad JSON
            API-->>LLM: Exception / non-JSON text
            LLM-->>Caller: empty buckets {} + warning log
            Caller->>Rule: extract_truth/reasoning/memory()
            Rule-->>Caller: buckets
        end
    end

    Caller->>Caller: detect_drift() + score_coherence()
    Caller-->>Caller: RefinedEpisode
```

## Confidence Clamping

Ensures LLM-returned confidence values are always valid regardless of model output.

```mermaid
flowchart TD
    RAW["LLM returns confidence\ne.g. 1.5 / -0.2 / 'high' / null"] --> TRY{float(v)?}
    TRY -->|success| CLAMP["max(0.0, min(1.0, v))"]
    TRY -->|ValueError / TypeError| DEF["default = 0.5"]
    CLAMP --> OUT2[Valid confidence 0.0–1.0]
    DEF --> OUT2

    style RAW fill:#1a1a2e,stroke:#e94560,color:#fff
    style OUT2 fill:#0f3460,stroke:#533483,color:#fff
```

## System Prompt

The instruction sent as the `system` parameter on every API call.

```
You are an institutional knowledge extractor for Σ OVERWATCH.
Given an AI decision episode transcript, extract structured knowledge.
Return ONLY valid JSON matching the schema below.
No explanation, no markdown fences.

{
  "truth": [{"claim": str, "confidence": float, "evidence": str}],
  "reasoning": [{"decision": str, "confidence": float, "rationale": str}],
  "memory": [{"entity": str, "entity_type": str, "relations": [str], "confidence": float}]
}
```
