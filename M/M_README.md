# VINCULUM Runtime v0.5.0 — Consolidated Baseline
## Deep Sigma Model-Adjacent Coherence Harness

> **VINCULUM surrounds the model. Deep Sigma governs what crosses the boundary.**
>
> **Machine-speed coherence. Human-speed authority.**

v0.5 consolidates the fragmented v0.1–v0.4 prototypes into one package and deliberately stops duplicating capabilities already present in Deep Sigma Core.

## Canonical split

- **Deep Sigma Core** — canonical CERPA, drift, Memory Graph, authority, PRIME/coherence-gate capabilities when installed.
- **VINCULUM Runtime** — model harness, context boundary, replaceable model adapters, human escalation surface.
- **Deep Sigma Autonomy Coherence / MERIDIAN** — autonomy application: coordinates, autonomy loop, mission testing, degraded ops, multi-agent coherence.
- **JIT (2016)** — verification / correspondence to reality. No later correction-loop mechanism is retroactively inserted.
- **ONG (2020)** — Orientation / Navigation / Guidance as movement through knowledge. No later correction-loop mechanism is retroactively inserted.
- **TRM (2024–25)** — Truth / Reasoning / Memory coherence substrate; the correction loop emerges in this phase.

## Coordinates

`TIME → MEMORY → ORIENTATION`  
`LANGUAGE → REASONING → NAVIGATION`  
`MATH → TRUTH → GUIDANCE`

Memory tells autonomy where it is. Reasoning tells autonomy how to move. Truth tells autonomy whether it should.

## New in v0.5

- package refactor under `vinculum/`
- zero-dependency OpenAI-compatible model adapter + LM Studio specialization
- explicit Deep Sigma Core bridge instead of a second CERPA engine
- mission testing baseline-vs-enabled metrics
- distributed agent/team/mission coherence objects
- connected/degraded/disconnected/rejoining/reconciling states
- DoD-oriented evidence profile (not a compliance certification)
- bounded transition-evidence run object
- historical lineage modules for JIT and ONG
- tests that enforce the historical invariant that JIT/ONG do not contain the later correction-loop construct

## Recovered prior pyLib lines

- **VINCULUM Folding / Origami** — Time·Words/Language·Numbers/Math episodes, reversible unfolding, evidence-preserving folds, hash-linked SQLite editions.
- **Deep Sigma Cartography** — governed semantic maps, evidence/authority/dependency paths, impact and cycles, versioned editions; proposes but does not approve/APPLY.
- **envHarness** — controlled discriminating-test selector for semantic residuals; JEPA may be an optional predictor adapter, never an automatic authority.
- **Zipf Compensator** — evidence-review prioritization with copied-source de-amplification and mandatory-alert separation; not a truth engine.
- **Liddell Lens** — comparative measurement of preparation/review burden and benefit; measurement only.
- **Trinity / Nano Sigma ports** — integration contracts only; PATHFINDER/RESONATOR/COMPOSER and LatticeDB remain separate engines.

## Quick start

```bash
python -m vinculum.cli --about
python -m vinculum.cli --probe-core
python -m vinculum.cli --model <id> --context fixtures/example_context.json --prompt "Assess this autonomy decision."
```

LM Studio defaults to `http://localhost:1234/v1`.
