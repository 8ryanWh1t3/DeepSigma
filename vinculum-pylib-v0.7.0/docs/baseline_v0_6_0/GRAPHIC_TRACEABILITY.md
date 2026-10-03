# Approved-graphic accommodation and corrections

Basis: the two approved “Cross-order semantic-numeric hinge” / “Reality to representation” graphics, the notebook lattice, and the user's subsequent scope corrections.

| Graphic concept | Implementation / disposition |
|---|---|
| Language and mathematics, each with P and D | `Representation.side`, `PDProfile`; no side-specific new-path baseline |
| Five orders on each side | Positive `order`; default L/M five-order legends; extensions beyond five supported |
| Cross-order diagonals | Arbitrary explicit endpoint pairs, not only i=j |
| Hinge only exists for pairs | `PairSpec`, `PairResult`; unpaired nodes have no collision result |
| Hinge can carry P/D at multiple orders | `HingeOrderState`, serialized pair-local assessments |
| 5×5 order matrix | Sparse `PairGraph` view; 25 possible positions, not 25 automatic comparisons |
| Same entity/property/scope/method/evidence | Required and descriptive hinge checks, source/dependence metadata |
| Probability, uncertainty, exactness | Explicit intervals, support coefficients, missing support and P/D descriptors |
| Third-state output | Comparability, discrepancy, support, coverage, outcome and separate score indicators |
| Codec / LLM translation | `CodecEvaluator` over declared source/target semantic-numeric inventories |
| Pairing monitor | Bounded normalized-event monitor, proposals, ambiguity and explicit selection |
| Claim / episode / document / graph / corpus | `ObjectGroup` hierarchy and distinct-pair aggregation |
| JSON / RDF / Excel / UI | Strict JSON; native Turtle; explicit generic field map; CSV; optional XLSX; offline HTML |
| Pluggable extraction/models | `RepresentationAdapter` / `AdapterRegistry`; custom hinge checks; no hosted model built in |
| Origin and retreat path | Attributed `NarrativeContext`, not scored or passed into numeric evaluation |
| Human authority / action | Application boundary; no command, permission, or CERPA APPLY code added |

## Important corrections to concept-image text

- A known subject/type mismatch is NOT_COMPARABLE, not CONFLICT. The first graphic conflated them.
- UNKNOWN/missing is not false, zero, agreement, or low risk.
- “25 possible pairings” means possible order positions. Each position may have zero or several selected object pairs.
- Graphics' v2.0 labels and example imports were design illustrations, not proof of a shipped package or API.
- “Preserve truth” is not a software guarantee. The implemented task is to test preservation of declared representations and numeric implications.
- “God → Big Bang → …” is the user's narrative/theological framing, not a causal theory implemented by the scoring engine. Retreat is a presentation path, not reverse physical time or a numeric spiritual metric.
- Neither a high conflict coefficient nor any result authorizes operational action.

These distinctions are implemented and tested rather than silently adopting unsupported guarantees from an image.
