# Deep Sigma pyOntology v0.1.0

**Modular ontology federation that prevents ontology silos without forcing one giant ontology.**

> Local ontology. Enterprise meaning.

## What it does

- Loads RDF / OWL / SKOS Turtle modules.
- Registers module identity, namespace, owner, version, authority, dependencies and fingerprints.
- Builds a searchable enterprise semantic registry.
- Detects same-label/different-URI semantic collisions across modules.
- Discovers candidate cross-module bridges without auto-asserting equivalence.
- Gates creation of new concepts with `REUSE / LINK / SPECIALIZE / REVIEW / CREATE` guidance.
- Preserves human authority over semantic equivalence.
- Detects ontology drift with graph + term-level diffs.
- Supports optional SHACL validation.
- Provides a CLI for pipeline use.

## Install

```bash
python -m pip install -e .
```

Optional SHACL:

```bash
python -m pip install -e '.[shacl]'
```

## Quick start

```python
from pyontology import Fabric, OntologyModule

fabric = Fabric("deep-sigma", "semantic_registry.sqlite")

core = OntologyModule.load(
    "examples/ontologies/coherence_ops_v2.ttl",
    "examples/manifests/coherence_ops_v2.module.json",
)

lenses = OntologyModule.load(
    "examples/ontologies/coherence_ops_lenses_v2.1.ttl",
    "examples/manifests/coherence_ops_lenses_v2.1.module.json",
)

fabric.register(core)
fabric.register(lenses)

print(fabric.search("decision"))
print(fabric.detect_collisions())
print(fabric.discover_bridges(threshold=0.85))
```

## Prevent a new silo

```python
proposal = fabric.propose_concept(
    target_module="cuas",
    label="Installation",
    kind="Class",
)

print(proposal.recommended_action)
# REUSE / LINK / SPECIALIZE / REVIEW / CREATE
```

Default concept creation is gated:

```python
fabric.add_concept(
    target_module="cuas",
    uri="https://deep-sigma.io/cuas#Installation",
    label="Installation",
    mode="CHECK_FIRST",
)
```

If overlapping enterprise meaning exists, `SemanticCollisionError` is raised until a human explicitly chooses the semantic posture.

## CLI

```bash
pyontology inspect ontology.ttl
pyontology validate a.ttl b.ttl
pyontology collisions a.ttl b.ttl
pyontology bridges --threshold 0.85 a.ttl b.ttl
pyontology search "installation" a.ttl b.ttl
pyontology diff old.ttl new.ttl
```

## Current boundaries

v0.1.0 deliberately does **not**:

- auto-merge ontologies;
- auto-accept `owl:equivalentClass` or `skos:exactMatch`;
- act as the enterprise source of authority;
- replace a triplestore;
- perform embedding-based semantic matching.

Those are controlled expansion points, not omissions. The first version establishes the federation contract before adding probabilistic semantic discovery.

## CI semantic gate

Use the creation gate in a build pipeline before minting a new enterprise URI:

```bash
pyontology gate-create \
  --target-module coherence_ops_lenses_v2.1 \
  --label "Decision" \
  examples/ontologies/coherence_ops_v2.ttl \
  examples/ontologies/coherence_ops_lenses_v2.1.ttl
```

Exit code `0` means no material overlap was found. Exit code `3` means creation requires a governed `REUSE`, `LINK`, `SPECIALIZE`, or human `REVIEW` decision.
