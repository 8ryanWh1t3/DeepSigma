# Decision Operations Ontology (DOO) v0.2 — Modular Draft

DOO is a vendor-neutral RDF/OWL vocabulary for representing how decisions are framed, supported, authorized, made, executed, reviewed, corrected, and remembered.

## Architectural rule

**DOO describes how a decision exists. Coherence Ops describes how an organization operates around decisions.**

An organization can deploy DOO without installing Deep Sigma, Coherence Ops, CERPA, PATHFINDER, RESONATOR, COMPOSER, Nano Sigma, or VINCULUM.

## Modules

| File | Purpose | Required? |
|---|---|---|
| `doo-core.ttl` | DecisionEpisode, problem, context, criteria, options, decision, action, outcome, actors | Yes |
| `doo-evidence.ttl` | Claims, evidence, assumptions, observations, uncertainty, contradictions, sources | Optional |
| `doo-authority.ttl` | Authority, roles, approvals, scope, jurisdiction, constraints, policy basis | Optional |
| `doo-lifecycle.ttl` | States, review, triggers, drift, patches, invalidation, supersession | Optional |
| `doo-memory.ttl` | Decision lineage, reflection, drift records, memory graph, portable packets | Optional |
| `doo-provenance.ttl` | W3C PROV-O alignment | Optional but recommended |
| `doo-shapes.ttl` | SHACL baseline validation profile | Optional |
| `doo-all.ttl` | Convenience import of all vendor-neutral OWL modules | Optional |
| `doo-coherenceops.ttl` | Optional mapping to Deep Sigma Coherence Ops and prior DOO v0.1 terms | Deep Sigma only |

## Universal semantic spine

`Context → Problem → Claims/Evidence/Assumptions → Options → Decision → Authority → Action → Outcome → Review → Drift → Patch → Memory`

Not every implementation must instantiate every element. The core ontology remains intentionally small; additional modules add governance and assurance without changing the basic decision object model.

## Interoperability principles

1. **Vendor neutral** — no commercial platform is required.
2. **System neutral** — graph stores, relational stores, event systems, documents, agents, and spreadsheets can all project into DOO.
3. **Provenance reuse** — DOO aligns to W3C PROV-O rather than inventing a parallel provenance model.
4. **Modularity** — systems import only the semantic capabilities they need.
5. **Stable identity** — decision objects should carry durable identifiers independent of UI or storage technology.
6. **Human authority remains explicit** — the ontology can represent authority; it does not originate authority.
7. **Portable decision episodes** — a decision and its justification can move across systems without losing meaning.

## Minimum deployment

A minimal DOO implementation needs only:

- `DecisionEpisode`
- `DecisionProblem`
- one or more `DecisionOption`
- `Decision`
- `Actor`
- `Action` / `Outcome` when execution is tracked

For governed environments, add Evidence + Authority + Lifecycle + Provenance.

## Namespace status

The v0.2 draft uses `https://decisionoperations.org/ontology/...` as the **proposed neutral canonical namespace**. Before a 1.0 public standard, this URI should be bound to a domain or persistent identifier controlled by the project so terms are durably dereferenceable.

## Deep Sigma relationship

Deep Sigma's Coherence Ops remains the operational architecture. `doo-coherenceops.ttl` is only an optional profile that maps neutral DOO concepts to Coherence Ops, including existing Claim/Evidence/Assumption/Decision/Patch concepts and the DLR/RS/DS/MG family.

## Version migration

DOO v0.1 used `https://deepsigma.io/ontology/decision-operations#`. The Coherence Ops profile includes compatibility equivalences for the major v0.1 classes so existing prototypes can migrate without discarding prior data.

## Licensing recommendation

For universal external adoption, publish the ontology under a permissive public license (for example CC BY 4.0 or CC0) after legal review, and version the ontology independently from Deep Sigma application releases.
