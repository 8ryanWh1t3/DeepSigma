# VINCULUM v0.5 Architecture

## Scope reset

v0.5 makes VINCULUM a measurement engine again. Its job is not to authorize, publish, govern, sign, or approve. Its job is to quantify the P↔D relationship of a bounded object.

## The asymmetric model

### Language — offensive P→D
Natural language begins with interpretation. VINCULUM looks for deterministic anchors that reduce ambiguity: definitions, explicit identifiers, units, dates, bounds, logical operators, RDF/SKOS/OWL semantics, citations, and explicit relations.

### Mathematics — defensive D←P
Mathematics begins with formal structure. VINCULUM measures deterministic structure while detecting probabilistic pressure such as approximation, measurement error, confidence, distributions, estimates, and explicit uncertainty.

### Formal semantics / TTL
RDF/Turtle is already formal, but it is not automatically complete or unambiguous. VINCULUM therefore measures parseability, stable IRI identity, typed literals, standard vocabulary use, blank-node identity, and natural-language literal pressure.

## Third state

VINCULUM never collapses P and D into one opaque confidence number. It preserves both and derives their relationship:

`ΣV = {P, D, V, τ, Coverage}`

This makes a boundary case observable rather than hiding it inside an average.

## Recursion

Leaf objects are scored directly. Composite objects aggregate child scores by explicit weights.

```text
RDF Triple → TTL Graph
Claim → Paragraph → Document → Corpus
Claim/Event/Decision → Episode
Row → Dataset
```

Weighted roll-up:

```text
P_object = Σ(w_i * P_i) / Σw_i
D_object = Σ(w_i * D_i) / Σw_i
Coverage_object = Σ(w_i * Coverage_i) / Σw_i
```

TTL graphs additionally retain a small graph-structure overlay for parse validity and graph-level formal structure.

## Deterministic scoring

The default scorers are explicit regex/structural rules with named weights. There is no hidden model call. Every P/D driver appears in the result so operators can see why the score moved.

Configuration is inspectable through `ScoringConfig` and `SignalRule`.

## Boundaries

VINCULUM does not claim:

- factual truth
- legal validity
- organizational authority
- policy compliance
- human intent
- semantic completeness
- causal correctness

It measures the P/D character of the object supplied to it.
