# Scoring Model

## Raw channels

P and D are independent channels in `[0,1]`.

### Language defaults
- baseline P = 0.45
- baseline D = 0.15

This encodes the design assumption that ordinary language leans probabilistic.

P drivers include hedges, likelihood, appearance/inference language, approximation, assumptions, explicit uncertainty, generalizers, and opinion markers.

D drivers include explicit definitions, mandates, quantified bounds, stable identifiers/URIs/hashes, ISO dates, number+unit pairs, formal logic, explicit relations, RDF/SKOS/OWL anchors, and citations.

### Math defaults
- baseline P = 0.05
- baseline D = 0.65 when mathematical structure is detected

P drivers include approximate equality, ± uncertainty, confidence/probability language, stochastic/distribution constructs, estimates and uncertainty.

D drivers include equality, inequalities, arithmetic operators, formal functions/operators, exact ratios, and explicit units.

### Structured data defaults
- baseline P = 0.15
- baseline D = 0.45

Null/missing fields increase unresolved pressure and reduce coverage. Typed/numeric scalar structure increases D.

### TTL defaults
- baseline P = 0.05
- baseline D = 0.75 for a valid parse

IRI subjects/predicates/objects, typed literals, and standard semantic-vocabulary predicates increase D. Blank nodes, untyped natural-language literals, and parse failure increase P.

## Saturation

Repeated signals have diminishing returns:

```text
score = baseline + (1-baseline) * (1-exp(-signal_sum/scale))
```

This prevents a long document from becoming deterministic merely because the same keyword repeats hundreds of times.

## VINCULUM vector

Given raw P and D:

```text
p = P/(P+D)
d = D/(P+D)
V = d-p
V_score = 50*(V+1)
τ = 1-|V|
intensity = (P+D)/2
tension_index = τ*intensity*Coverage
usable_value = 50*(1 + V*Coverage)
```

### Why two tension values?
`τ` measures balance only. P=.1/D=.1 and P=.9/D=.9 are equally balanced but not equally consequential. `tension_index` multiplies balance by intensity and coverage, making strong competition distinguishable from weak equilibrium.

## Interpretation bands

- `<40`: PROBABILISTIC_DOMINANT
- `40–60`: BOUNDARY_TENSION
- `>60`: DETERMINISTIC_DOMINANT
- coverage `<0.15`: UNMEASURED

These thresholds are configurable.

## Important caveat

The score is not truth. It is entirely possible for a highly deterministic statement to be false and a highly probabilistic statement to be correct.
