# Mini Graph Walkthrough (Toy Example)

## Scenario
A decision was made and sealed. It references a claim supported by evidence derived from a source (doc/policy).

## Graph
- `:DEC_1` (Decision)
- `:CL_1`  (Claim)
- `:EV_1`  (Evidence)
- `:SRC_42` (Source)

## Query
Run `queries/dlr_why_decision.sparql` to retrieve:
- claim, evidence, source chain

## Why this matters
Instead of “find the file,” you can answer:
- Why was this decided?
- What evidence supported it?
- What policy/source does it depend on?
- What breaks if the source changes?
