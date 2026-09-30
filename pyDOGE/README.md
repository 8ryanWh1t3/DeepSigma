# pyDOGE

**Diagnose work before workforce.**

`pyDOGE` is a Deep Sigma / Post-Taylorism Python library for making organizational work explainable before anyone tries to optimize headcount.

Its operating chain is:

```text
MISSION → AUTHORITY → POLICY → WORK → DEPENDENCIES → SYSTEMS → PEOPLE → OUTCOME
```

The library asks **why work exists, what creates it, what it depends on, where it waits, where it repeats, what breaks if it changes, and what should be redesigned or automated**.

## Non-negotiable guardrail

> **pyDOGE scores work architecture, not employees.**

It contains no employee ranking or individual productivity score. Workforce implications are deliberately downstream of redesigned work.

## What it does

- maps mission → authority → policy → work lineage
- detects orphan work with no mission/policy binding
- surfaces duplicate-work candidates for human review
- estimates rework and handoff latency
- detects dependency cycles
- calculates downstream blast radius
- flags outcome drift
- identifies bounded automation candidates
- estimates architecture-level workload and labor cost
- explains **"Why does this work exist?"**
- provides a minimal CERPA ledger: **Claim → Event → Review → Patch → Apply**

## Install locally

```bash
python -m pip install -e .
```

## Run the demo

```bash
python examples/demo.py
```

## CLI

```bash
pydoge analyze examples/agency.json
pydoge explain examples/agency.json W2
pydoge blast-radius examples/agency.json W1
pydoge map examples/agency.json
```

## Python API

```python
from pydoge import WorkSystem

org = WorkSystem.load("examples/agency.json")

org.map_work()
org.trace_authority("W2")
org.find_duplicate_work()
org.find_rework()
org.find_handoff_latency()
org.find_orphan_tasks()
org.find_automation_candidates()
org.calculate_blast_radius("W1")
org.explain("W2")

report = org.optimize()
```

## Optimization order

`optimize()` deliberately sequences intervention as:

```text
VALIDATE necessity
→ CONSOLIDATE duplicate work
→ REDESIGN handoffs
→ PATCH rework
→ AUTOMATE bounded work
→ SIZE workforce capacity from the redesigned system
```

The final step is **SIZE**, not the first step.

## Dataset shape

See `examples/agency.json`. The core objects are:

- `Mission`
- `Authority`
- `Policy`
- `WorkItem`
- `SystemAsset`
- `RoleCapacity`
- `OutcomeObservation`

A `WorkItem` contains mission/policy/system/role bindings plus dependencies, cycle time, touch time, volume, rework, approval gates, and outputs.

## Design status

This is **v0.1.0**, an executable architecture/MVP. The algorithms are deliberately transparent and deterministic. Findings such as duplicate work or automation candidates are review signals, not autonomous decisions.

## Deep Sigma thesis

> **Make the system explainable before optimizing it.**
