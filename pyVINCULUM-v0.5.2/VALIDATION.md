# Validation — VINCULUM pyLib v0.5.2

## Release target

**Second-Order P↔D Tension Engine — words and numbers collide, with uncertainty on both sides.**

Canonical second-order model:

```text
LANGUAGE:  P_L → D_L   with S_L
MATH:      D_M ← P_M   with R_D and U_D

D_effective = D_raw * R_D
U_D = 1 - R_D
C_V = C_raw * S_L * R_D
```

## Source validation

- Python compileall: **PASS**
- Unit tests from source: **74 / 74 PASS**
- Failures: **0**
- Errors: **0**

Coverage includes:

- v0.5.0 P↔D formulas and recursive roll-up
- v0.5.1 semantic determinization and record reconciliation
- exact math retains full deterministic defense
- approximate math weakens deterministic defense
- explicit `reliability 55%` → `R_D=.55`, `U_D=.45`
- postfix `80% confidence` normalization
- structured record confidence changes `D_effective` and collision strength
- structured record uncertainty does **not** double-count into first-order P
- C-UAS words=`airspace clear` vs count=`1` strong/weak sensor cases
- TTL same-subject confidence weakens record defense
- collision alias/output contract
- conservative pairing / unresolved ambiguous cases

## Wheel validation

- wheel build: **PASS**
- wheel: `vinculum_pylib-0.5.2-py3-none-any.whl`
- wheel SHA-256: `c1679f195bfa83a679da458743de2b35cdebd767935b87277910beaa8919818a`
- install into isolated target: **PASS**
- tests against installed wheel: **74 / 74 PASS**
- installed `vinculum.__version__`: **0.5.2**

## C-UAS second-order smoke

Domain rule:

```text
"Airspace clear" → active-threat count = 0
S_L = .95
```

Observed value in both cases:

```text
active-threat count = 1
```

Strong sensor:

```text
R_D=.99
U_D=.01
D_raw=.95
D_effective=.9405
collision_strength=.65835
```

Weak sensor:

```text
R_D=.42
U_D=.58
D_raw=.95
D_effective=.399
collision_strength=.27930
```

The observed number remains `1`; only its deterministic defense changes. First-order P remains the same across the two structured-record cases.

The collision is additionally multiplied by conservative pairing alignment (`0.70` in this standalone singleton example). Pair discovery is intentionally separate from second-order scoring.

## Scope check

No governance, authority, approval, command-action, Policy Fence, or LLM semantics were added.

**PASS: v0.5.2 remains scoped to measuring the collision between word-implied numeric expectation and observed numeric state.**
