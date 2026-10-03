# VINCULUM pyLib v0.5.2 — Second-Order P↔D Tension Engine

**Canonical purpose:** measure what happens when words and numbers collide.

VINCULUM converts language into an expected numeric state, compares that expectation with an observed numeric state, and measures the collision. v0.5.2 adds the missing **second-order math variable**: a number may be explicit yet still be probabilistically contaminated by sensor confidence, measurement error, tolerance, estimation, or model uncertainty.

## Core model

```text
LANGUAGE:     P → D
MATHEMATICS:  D ← P
```

First order asks:

```text
What number do the words imply?
What number does the record show?
```

Second order asks:

```text
How strongly do the words determinize?         S_L
How strongly can the number defend determinism? R_D
How much probability contaminates the number?   U_D = 1 - R_D
```

The base VINCULUM vector remains stable:

```text
ΣV = { P, D, V, τ, Coverage }
```

with:

```text
p = P / (P + D)
d = D / (P + D)
V = d - p
V_score = 50 * (V + 1)
τ = 1 - |V|
intensity = (P + D) / 2
tension_index = τ * intensity * Coverage
usable_value = 50 * (1 + V * Coverage)
```

## Second-order math defense

For the numeric side:

```text
D_raw = first-order deterministic structure
U_D   = probabilistic contamination
R_D   = 1 - U_D
D_effective = D_raw * R_D
```

Examples of `U_D` include:

- sensor confidence below 1.0
- measurement uncertainty (`±`)
- approximate equality (`≈`)
- stated reliability
- estimation language
- stochastic / distributional constructs

If an explicit reliability is supplied, VINCULUM uses it directly. Otherwise math uncertainty signals derive a bounded `U_D`.

## Collision formula

A safely paired semantic expectation and numeric record use:

```text
C_raw = disagreement_basis * alignment
C_effective = C_raw * S_L * R_D
```

For exact equality, a mismatch is categorical (`disagreement_basis = 1`). The numerical delta is still retained separately.

Object-level:

```text
semantic_record_tension = mean(C_effective)
```

So the same words and same number can produce different collision strength depending on how strongly the number is defended.

## C-UAS example

Words:

```text
"Airspace clear."
```

Domain rule:

```text
"airspace clear" → active-threat count == 0
S_L = 0.95
```

Observed record:

```text
active-threat count = 1
```

### Strong sensor

```text
R_D = 0.99
U_D = 0.01
```

Result: strong contradiction.

### Weak sensor

```text
R_D = 0.42
U_D = 0.58
```

Result: the numeric value still says `1`, but it cannot defend determinism nearly as strongly. The collision remains visible while its strength falls.

That is the v0.5.2 distinction:

> **A number is not deterministic merely because it is numeric. It defends determinism only to the degree the variables producing it are deterministic.**

## Structured confidence / reliability

VINCULUM recognizes local second-order record keys such as:

```text
deterministic_defense
record_confidence
sensor_confidence
measurement_confidence
reliability
confidence
certainty
quality_score
```

Values may be `0..1`, `0..100`, or percentage strings such as `"42%"`.

Example:

```python
{
    "label": "active threat tracks",
    "count": 1,
    "sensor_confidence": 0.42,
}
```

## Python example

```python
from vinculum import (
    MeaningRegistry,
    MeaningRule,
    ObjectType,
    VinculumEngine,
    ingest_mapping,
)

clear = MeaningRule.compile(
    id="SEM_AIRSPACE_CLEAR",
    label="airspace clear",
    pattern=r"\bairspace\s+(?:is\s+)?clear\b",
    dimension="count",
    operator="eq",
    value=0,
    unit="count",
    confidence=0.95,  # S_L
    priority=5,
)

engine = VinculumEngine(
    meaning_registry=MeaningRegistry.default().with_rule(clear)
)

obj = ingest_mapping(
    {
        "claims": ["Airspace clear."],
        "observations": [
            {
                "label": "active threat tracks",
                "count": 1,
                "sensor_confidence": 0.42,  # R_D
            }
        ],
    },
    object_type=ObjectType.EPISODE,
    object_id="CUAS-SECOND-ORDER",
)

result = engine.score(obj)

print(result.semantic_record_tension)
print(result.deterministic_defense_strength)  # R_D
print(result.probabilistic_contamination)      # U_D
print(result.raw_deterministic_strength)       # D_raw
print(result.defended_deterministic_strength)  # D_effective
```

## Stable output

The original `Sigma_V` contract is unchanged. v0.5.2 adds a `second_order` block:

```json
{
  "Sigma_V": {"P": 0.30, "D": 0.399, "V": 0.1416, "tau": 0.8584, "Coverage": 1.0},
  "second_order": {
    "S_L_semantic_determinization_strength": 0.95,
    "R_D_deterministic_defense_strength": 0.42,
    "U_D_probabilistic_contamination": 0.58,
    "D_raw_first_order_determinism": 0.95,
    "D_effective_defended_determinism": 0.399
  }
}
```

## Install

```bash
pip install vinculum_pylib-0.5.2-py3-none-any.whl
```

Runtime dependency: `rdflib>=7.0`. No LLM dependency.

## Scope boundary

VINCULUM does not decide factual truth, legal authority, permission, policy compliance, or command action.

It measures:

1. what number words imply,
2. what number the record states,
3. how strongly the words determinize (`S_L`),
4. how strongly the numeric record defends determinism (`R_D`),
5. how much probabilistic contamination weakens that defense (`U_D`),
6. and the resulting collision/tension.

See `SCORING_MODEL.md`, `SECOND_ORDER_DEFENSE.md`, `SEMANTIC_RECONCILIATION.md`, and `ARCHITECTURE.md`.

### Important second-order separation

For a structured numeric record, `U_D` weakens `D_effective`; it is **not automatically counted again as new first-order P pressure**. This keeps the second-order variable conceptually separate from the original P channel. Math notation such as `≈` or `±` may still raise first-order P because those symbols themselves explicitly encode probabilistic/approximate meaning.

### Pairing remains conservative

v0.5.2 measures collision only after semantic and numeric facts are safely paired. Pair alignment remains a distinct factor from `S_L` and `R_D`. A future monitor can improve pairing confidence without changing the VINCULUM scoring core.
