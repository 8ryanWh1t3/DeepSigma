---
title: "Category Declaration — Institutional Decision Infrastructure"
version: "1.0.0"
status: "Canonical"
last_updated: "2026-02-16"
---

# Institutional Decision Infrastructure

## The Category

Institutional Decision Infrastructure is a new category of software that governs the lifecycle of autonomous decisions — from the moment truth is gathered, through reasoning and action, to sealed memory and self-correction.

It sits between the agent framework (which makes decisions) and the data platform (which stores things). It answers the question that neither can:

> When an autonomous system makes a decision, can you prove — months later — what was true, why it reasoned that way, and what the institution remembers?
>
> ## What This Is Not
>
> | Existing Category | What It Does | What It Misses |
> |-------------------|-------------|----------------|
> | Observability (Datadog, Splunk) | Monitors metrics and logs | Cannot reconstruct *why* a decision was made or whether the truth was fresh |
> | ML Governance (MLflow, Weights & Biases) | Tracks model training and experiments | Does not govern runtime decisions, action safety, or drift correction |
> | Workflow Orchestration (Airflow, Temporal) | Sequences tasks | No concept of truth freshness, degrade ladders, or sealed provenance |
> | GRC / Compliance (Archer, ServiceNow) | Manages risk registers and policies | Static policy; no runtime enforcement, no drift detection, no self-correction |
>
> Institutional Decision Infrastructure is the **runtime governance layer** that makes autonomous decisions auditable, correctable, and institutional.
>
> ## The Operating Metaphor: The Decision Office
>
> Think of it like Microsoft Office — but for decisions:
>
> | Office Tool | Decision Office Equivalent |
> |-------------|---------------------------|
> | Word (document creation) | DTE + Action Contract (decision definition) |
> | Excel (calculation) | Claims + Rationale Graph (truth computation) |
> | Outlook (communication) | Drift Signals + Patch Queue (feedback loop) |
> | OneNote (memory) | Memory Graph + IRIS (institutional recall) |
> | Audit trail | Sealed Episodes + DLR (immutable receipts) |
>
> You don't need all of it at once. Start with sealing episodes and extracting DLRs. Add drift detection when you're ready. Add the Memory Graph when you need "why did we do this?" retrieval.
>
> ## Learn More
>
> - [The Triad: Truth · Reasoning · Memory](../ontology/triad.md)
> - - [The Four Artifacts: DLR / RS / DS / MG](../canonical/prime_constitution.md)
>   - - [End-to-End Demo](../examples/demo_walkthrough.md)
>     - - [Positioning: How IDI Differs](positioning.md)
