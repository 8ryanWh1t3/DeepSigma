# VINCULUM pyLib v0.5.0 — P↔D Tension Engine

**Canonical purpose:** measure where any bounded object sits between probabilistic interpretation and deterministic constraint, measure the tension between those forces, and produce a reusable value at any scale.

VINCULUM v0.5 resets the library to its original scope. The governance-heavy work from v0.3/v0.4 is **not** the core engine. Those releases remain historical/adapter work; v0.5 is the canonical measurement kernel.

## Core model

Language naturally leans probabilistic and VINCULUM pushes it toward determinism:

```text
LANGUAGE: P → D
```

Mathematics naturally leans deterministic and VINCULUM measures/defends it against probabilistic contamination:

```text
MATHEMATICS: D ← P
```

Their interaction produces a third state:

```text
ΣV = { P, D, V, τ, Coverage }
```

with:

```text
p = P / (P + D)
d = D / (P + D)
V = d - p                         # -1 ... +1
V_score = 50 * (V + 1)           # 0 ... 100
τ = 1 - |V|                       # balance tension
intensity = (P + D) / 2
tension_index = τ * intensity * Coverage
usable_value = 50 * (1 + V * Coverage)
```

`V_score` is positional: 0 = strongly probabilistic, 50 = P/D boundary, 100 = strongly deterministic.

`τ` says how close P and D are to equilibrium. `tension_index` additionally accounts for how strong the two forces are and how much of the object was actually measured.

`usable_value` damps the directional score toward 50 when coverage is incomplete.

## This is not a truth score

A deterministic statement can be exactly wrong. A probabilistic statement can be correct. VINCULUM measures **form, pressure, constraint, and tension**—not ground-truth correctness, legal authority, or permission.

That separation is intentional.

## One engine, many object sizes

Supported object types include:

- Claim
- Episode
- Clause
- Paragraph
- Document
- Dataset / data row
- RDF triple
- Turtle / TTL graph
- Policy
- Decision
- Model output
- Sensor observation
- Corpus
- Math expression
- Generic bounded object

Composite objects recursively inherit weighted P/D values from children. A document can therefore roll up paragraphs; an episode can roll up claims/events/decisions; a TTL graph can roll up RDF triples; a corpus can roll up documents.

## Install

```bash
pip install vinculum_pylib-0.5.0-py3-none-any.whl
```

Runtime dependency: `rdflib>=7.0`. There is no LLM dependency.

## Python — claim

```python
from vinculum import VinculumEngine, ObjectType, ScoreMode, ingest_text

obj = ingest_text(
    "The track likely represents a UAS approximately 80 m north of checkpoint A.",
    object_type=ObjectType.CLAIM,
    mode=ScoreMode.LANGUAGE,
)
r = VinculumEngine().score(obj)
print(r.to_dict(include_children=False))
```

## Python — document

```python
obj = ingest_text(document_text, object_type=ObjectType.DOCUMENT)
r = VinculumEngine().score(obj)
print(r.vinculum_score, r.tension_index, r.usable_value)
```

## Python — TTL

```python
from vinculum import ingest_ttl
r = VinculumEngine().score(ingest_ttl(ttl_text))
print(r.to_dict())
```

## CLI

```bash
vinculum score "The claim may be correct" --type claim --pretty
vinculum score examples/document.txt --pretty
vinculum score examples/sample.ttl --pretty
vinculum score-json examples/episode.json --type episode --pretty
```

## Core pipeline

```text
INGEST
  ↓
DECOMPOSE
  ↓
SCORE P
  ↓
SCORE D
  ↓
NORMALIZE P:D
  ↓
DERIVE V + τ
  ↓
AGGREGATE CHILDREN
  ↓
ΣV + V_score + tension_index + usable_value
```

See `SCORING_MODEL.md` and `ARCHITECTURE.md` for the detailed design.
