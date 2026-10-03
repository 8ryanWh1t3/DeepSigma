# Requirements and source traceability

## Basis and precedence

The user's immediate request is to create the Cartography Python library module following the
conversation's governed semantic cartography definition and graphics. Those graphics are design
references, **not proof of implementation**. Earlier PATHFINDER ratings and test counts in a graphic
are not inherited by this new package. This package reports only its own executed tests.

Existing project sources constrain names, responsibilities, and trust boundaries. Implementation
choices below are newly authored in this release. Source aspirations such as automatic truth,
readiness guarantees, universal semantic equivalence, and economic ROI are not silently adopted.

| Requirement | Source basis | Implementation / boundary |
|---|---|---|
| Meaning, evidence, authority, dependencies, routes, legend, editions, unknowns | Cartography conversation | Atlas, MapView, Node/Edge/Evidence/Predicate, explicit statuses, traces, editions |
| DLR / RS / DS / MG remain canonical | COHERENCE_OPS_COMPLETE.docx, Four Artifacts | Preserves host identities/attributes; native MG adapter; does not redefine canonical artifacts |
| Reasoning/evidence memory and correction history | Same source, MG and Prime Packet sections | Source records, immutable application snapshots, diffs, content fingerprints |
| No people scoring | Same source, Non-Coercion by Construction | Structural artifact findings only; no person rankings or individual behavior scoring |
| Relationship meaning, incoming/outgoing paths, evidence, CERPA linkage | Phase 2 Target Review.txt, TripleStore and runtime sections | Explicit predicate semantics and native-shaped CERPA draft output |
| Preserve unknown vs absent | Cartography conversation | UNKNOWN status; missing evidence is a gap, not falsehood; no-path result says recorded route absent |
| Gap detection is explicit | RESONATOR.txt v0.9.4 / v0.10.0 notes | Eight default structural codes plus explicit coverage requirement code; not the entire native engine |
| Coverage differences are not automatically conflict | RESONATOR v0.9.4 and v0.10.0 notes | No natural-language gap inference or scalar alignment/compliance claim |
| Cartography cannot originate approval | PATHFINDER.txt, concluding attestation principle | No Apply or approval API; proposed Review/Patch records only |
| Do not rebuild the Fence as a product | COMPOSER.txt RC55 | No new trust-enrollment or authority engine; host retains governActualization boundary |
| Missing/corrupt archive is not genesis | COMPOSER RC5/RC6 trust lessons | Explicit create vs open, fail-closed chain validation, propagated write failure |
| Hash is not authority; rollback requires durable trusted context | Same trust reviews | Explicit local trust assumptions, independently pinned expected head; no production security claim |
| Preserve VINCULUM existing kernels | MIGRATION_V0_6_TO_V0_7.md | Separate add-on; no original kernel changes; proposed interchange only |
| Folding does not erase qualifications | Cartography conversation | All members/edges/statuses retained; reversible source view; no routing on group graph |
| CERPA reduces to a workbook | Established project convention | Optional 11-tab workbook, C/E/R/P/A plus dashboard/memory/evidence/legend/metadata |

## Inspected code, not guessed interfaces

Supplied archive: `DeepSigma-main (18).zip`.
Inspected files: `pyproject.toml`, `src/core/memory_graph.py`, `src/core/cerpa/models.py`.
The native MG export and Review/Patch constructors are included in optional integration tests;
those tests were executed against the supplied snapshot for this build. This does not verify the
latest live branch or the complete deployment. Exact baseline hashes are recorded separately.

## Public technical references consulted

These guide interoperability and storage choices, not claims that Deep Sigma invented them:

- Python sqlite3 transaction documentation: https://docs.python.org/3.11/library/sqlite3.html
- W3C RDF 1.1 Concepts: https://www.w3.org/TR/rdf11-concepts/
- Python packaging project layout: https://packaging.python.org/en/latest/tutorials/packaging-projects/

## Explicit non-implementations

No automatic NLP/LLM extraction, training, GIS/geospatial engine, natural-language truth test,
SKOS entailment, cryptographic human-identity verifier, trusted repository access control,
classification downgrade, actual Lattice log adapter, Anduril connection, operational command,
weapon-control function, native VINCULUM UI bridge, MERIDIAN module import, or end-to-end Composer
commit integration is claimed. No new graphics are rendered by the module.
