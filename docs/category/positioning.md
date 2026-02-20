---
title: "Positioning — How IDI Differs"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# Positioning

## The Gap

Agent frameworks (LangChain, AutoGen, CrewAI) make it easy to build agents. Monitoring tools (LangSmith, Datadog) make it easy to observe them. But neither solves the core institutional problem:

**Decisions degrade silently.** Context goes stale. Policies drift. The system makes worse decisions over time and nobody knows until something breaks visibly.

## Where Institutional Decision Infrastructure Fits

```
Agent Frameworks (LangChain, AutoGen, CrewAI, custom)
         |
         v
  Institutional Decision Infrastructure
  (Coherence Ops + Sigma OVERWATCH)
  "How to trust agents"
  Truth / Reasoning / Memory
  DLR / RS / DS / MG
  Decide > Seal > Drift > Patch > Remember
         |
         v
  Data & Action Platforms
  (Foundry, Power Platform, APIs, databases)
  "Where agents read and write"
```

## Key Differentiators

**1. Truth has a shelf life.** Every claim carries a TTL and a half-life. Stale truth is worse than no truth. The system enforces freshness at decision time, not after the fact.

**2. Decisions are sealed, not just logged.** A sealed episode is a tamper-evident, immutable, hash-verified record. It can be forensically reconstructed months later.

**3. Drift is a first-class concept.** The system does not wait for a human to notice degradation. It detects drift, types it, fingerprints it, tracks recurrence, and proposes patches automatically.

**4. Memory is a graph, not a table.** The Memory Graph links decisions, claims, drift signals, and patches via typed provenance edges. "Why did we do this?" is a query, not an investigation.

**5. The loop closes.** Decide then Seal then Drift then Patch then Memory then next decision. This is not a pipeline — it is a continuous governance loop.
