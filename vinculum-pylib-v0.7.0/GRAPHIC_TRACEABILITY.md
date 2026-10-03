# Attached architecture graphic traceability - v0.7.0

`SOURCE_MANIFEST.json` records the six attached image filenames and SHA-256 digests used as the design basis for this update. The images are design requirements, not executable specifications; where a diagram conflated categories, the typed library semantics take precedence and the correction is documented below.

| Source | Principal concept | v0.7.0 accommodation |
|---|---|---|
| IMG-01 | **When words and numbers collide**; semantic expectation, numeric defense, pairing monitor, cross-domain examples | Preserved by `lang`, `math`, `semantics`, v0.6 cross-order core, `pairing`, and pipeline findings. Numeric reliability/support does not rewrite the observed value. |
| IMG-02 | **Hinge & higher-order collision model**; five orders on both sides; meaning, measurement, pairing uncertainty | `Representation.order`, independent P/D profiles, `SupportFactor`, pair-owned `HingeOrderState`, higher-order diagnostics, typed scope/time/unit compatibility. |
| IMG-03 | **Big picture**; representation layer, hinge, orders matrix, synthesis/collision output | `NarrativeContext` stores attributed non-scored big-picture framing; `PairGraph` and `CrossOrderEngine` implement the sparse matrix and pair output. |
| IMG-04 | **INPUT -> RUNTIME -> OUTPUT** baseline | `VinculumPipeline`, `io`, `represent`, `pairing`, `evidence`, `ontology`, `findings`, `exports`, `pipeline_cli`, optional API/store. |
| IMG-05 | **Reality to representation / cross-order semantic-numeric hinge**; 5x5 matrix; retreat path | Five-order default view, arbitrary `L_i <-> M_j`, non-scored origin/retreat context. Pairing is by meaning/context, not by row equality. |
| IMG-06 | **Extended pyLib architecture**; module decomposition; outputs and integrations | Concrete modules for IO, representation, pairing, hinge, matrix, codec, reporting, ontology, evidence, utilities, API. Named enterprise platforms remain downstream targets only. |

## Core implementation truths

- Language and mathematics can each contain probabilistic **and** deterministic characteristics at every order.
- A hinge exists only for a selected pair; it is never an independent truth source.
- `L_i` may pair with any `M_j`; diagonal pairing is not privileged.
- The five orders are an extensible examination scaffold, not five mandatory certainty levels.
- A 5x5 display contains 25 possible order **positions**, not 25 mandatory object pairs.
- Unpaired material remains visible and has no collision score.
- Discrepancy, support, coverage, confidence-like coefficients, and status remain separate fields.
- Weak support does not erase a known mismatch; unknown support does not become zero risk.

## Corrections to concept-image wording

- A known entity/type/dimension mismatch is `NOT_COMPARABLE`, not `CONFLICT`.
- Missing required information is `UNRESOLVED`, not false or aligned.
- `PARTIAL` is used for admissible-set overlap where both agreement and disagreement remain possible.
- “Preserve truth” is not a software guarantee; the codec checks preservation of declared representations.
- “Decision” in the diagrams means a finding for downstream human/application review. VINCULUM itself performs no command action.
- “God -> Big Bang -> ...” and the retreat path are the user's philosophical/theological framing and remain attributed, non-scored presentation context.
- The graphics' `v2.0` labels are concept labels. The shipped artifact is **VINCULUM pyLib v0.7.0**.

## Downstream integration boundary

The attached graphics name Army/A365, Foundry, Vantage, OnBase, Lattice, PATHFINDER, RESONATOR, COMPOSER, and CERPA. v0.7.0 provides JSON/CSV/Turtle/HTML/PDF/XLSX/API surfaces that those systems may consume, but it contains no live connector, credentials, IAM implementation, sensor control, CERPA APPLY, or authoritative write path to those platforms.
