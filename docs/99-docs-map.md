# Docs De-Duplication Map

> **What:** A routing table that tells you where to find every topic — and flags where content overlaps.
>
> **So What:** Stop hunting. If you need X, this page tells you which file is the canonical source and which files duplicate it.

---

## Routing Table: "If You Need X, Read Y"

| You need… | Canonical source | Also mentioned in (secondary) |
|------------|-----------------|-------------------------------|
| Project vision & mission | [`docs/00-vision.md`](00-vision.md) | `category/declaration.md`, `README.md` |
| Terminology & naming | [`docs/01-language-map.md`](01-language-map.md) | `GLOSSARY.md`, `ontology/triad.md` |
| Core concepts (triad, loop) | [`docs/02-core-concepts.md`](02-core-concepts.md) | `ontology/triad.md`, `category/declaration.md`, `START_HERE.md` |
| Quickstart (run commands) | [`HERO_DEMO.md`](../HERO_DEMO.md) | `docs/05-quickstart.md`, `coherence_ops/README.md` |
| DLR specification | [`canonical/dlr_spec.md`](../canonical/dlr_spec.md) | `docs/20-dlr-claim-native.md`, `llm_data_model/02_schema/` |
| RS specification | [`canonical/rs_spec.md`](../canonical/rs_spec.md) | `llm_data_model/06_ontology/coherence_ops_alignment.md` |
| DS specification | [`canonical/ds_spec.md`](../canonical/ds_spec.md) | `llm_data_model/06_ontology/coherence_ops_alignment.md` |
| MG specification | [`canonical/mg_spec.md`](../canonical/mg_spec.md) | `llm_data_model/06_ontology/coherence_ops_alignment.md` |
| Claims / atomic claims | [`canonical/unified_atomic_claims_spec.md`](../canonical/unified_atomic_claims_spec.md) | `docs/19-claim-primitive.md`, `specs/claim.schema.json` |
| Coherence Ops integration | [`docs/10-coherence-ops-integration.md`](10-coherence-ops-integration.md) | `coherence_ops/README.md` |
| Policy packs | [`docs/11-policy-packs.md`](11-policy-packs.md) | `policy_packs/`, `engine/policy_loader.py` |
| Degrade ladder | [`docs/12-degrade-ladder.md`](12-degrade-ladder.md) | `engine/degrade_ladder.py` |
| Verifiers | [`docs/13-verifiers.md`](13-verifiers.md) | `verifiers/` |
| Replay / audit | [`docs/14-replay.md`](14-replay.md) | — |
| OpenTelemetry | [`docs/15-otel.md`](15-otel.md) | `adapters/otel/` |
| Supervised execution | [`docs/16-run-supervised.md`](16-run-supervised.md) | `engine/supervisor_scaffold.py` |
| Prompt → Coherence Ops | [`docs/17-prompt-to-coherence-ops.md`](17-prompt-to-coherence-ops.md) | — |
| IRIS query engine | [`docs/18-iris.md`](18-iris.md) | `wiki/IRIS.md`, `specs/iris_query.schema.json` |
| PRIME threshold gates | [`docs/18-prime.md`](18-prime.md) | `specs/prime_gate.schema.json` |
| DLR claim-native refactor | [`docs/20-dlr-claim-native.md`](20-dlr-claim-native.md) | `specs/dlr.schema.json` |
| JSON schemas | [`specs/`](../specs/) | `coherence_ops/schemas/`, `llm_data_model/02_schema/` |
| LLM data model | [`llm_data_model/README.md`](../llm_data_model/README.md) | `llm_data_model/06_ontology/coherence_ops_alignment.md` |
| Mermaid diagrams | [`mermaid/README.md`](../mermaid/README.md) | Individual `mermaid/*.md` files |
| Drift-to-patch flow | [`runtime/drift_patch_workflow.md`](../runtime/drift_patch_workflow.md) | `ontology/drift_patch_model.md`, `mermaid/05-drift-to-patch.md` |
| Sealing protocol | [`runtime/sealing_protocol.md`](../runtime/sealing_protocol.md) | `mermaid/14-seal-patch-lifecycle.md` |
| Category positioning | [`category/positioning.md`](../category/positioning.md) | `category/declaration.md` |

---

## Known Overlaps & Recommended Actions

| Overlap | Files | Recommendation |
|---------|-------|---------------|
| Quickstart commands | `docs/05-quickstart.md` vs `HERO_DEMO.md` vs `coherence_ops/README.md` | `HERO_DEMO.md` is the canonical hero path. `docs/05-quickstart.md` should link to it. `coherence_ops/README.md` keeps CLI-specific examples. |
| Core concepts | `docs/02-core-concepts.md` vs `ontology/triad.md` vs `category/declaration.md` | `docs/02-core-concepts.md` = narrative intro. `ontology/triad.md` = formal model. `category/declaration.md` = manifesto. Each has a distinct audience. |
| DLR spec | `canonical/dlr_spec.md` vs `docs/20-dlr-claim-native.md` vs `llm_data_model/02_schema/` | `canonical/dlr_spec.md` = normative spec. `docs/20-dlr-claim-native.md` = migration guide (additive). `llm_data_model/` = LLM-specific field mappings. |
| IRIS docs | `docs/18-iris.md` vs `wiki/IRIS.md` | `docs/18-iris.md` = canonical. `wiki/IRIS.md` should cross-link or be deprecated. |
| Coherence Ops architecture | `docs/10-coherence-ops-integration.md` vs `coherence_ops/README.md` | `coherence_ops/README.md` = library-level (modules, CLI). `docs/10-…` = integration guide (how to connect to RAL). No action needed. |
| Schema sources | `specs/` vs `coherence_ops/schemas/` vs `llm_data_model/02_schema/` | `specs/` = canonical JSON schemas. `coherence_ops/schemas/` = library-specific (manifest, report). `llm_data_model/02_schema/` = LLM field dictionary. |
| Terminology | `GLOSSARY.md` vs `docs/01-language-map.md` | `GLOSSARY.md` = quick lookup table. `docs/01-language-map.md` = detailed mapping with rationale. Both useful, no duplication. |

---

## Rule of Thumb

1. **Normative specs** live in `/canonical/`. If it defines how an artifact *must* behave, that’s the source of truth.
2. **JSON schemas** live in `/specs/`. They are the machine-readable version of the canonical specs.
3. **Operational guides** live in `/docs/`. They explain *how to use* the specs in context.
4. **Theory & ontology** live in `/ontology/`. They explain *why* the model works this way.
5. **LLM data model** lives in `/llm_data_model/`. It’s a parallel, LLM-optimized projection of the canonical model.
6. **If in doubt**, start at [`NAV.md`](../NAV.md) or [`START_HERE.md`](../START_HERE.md).
