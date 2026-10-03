# Hinge contract

`H(L_i, M_j; k)` means: examination order k of the hinge for language order i and mathematical order j. Same-side codec comparisons use their explicit side/order endpoints instead.

## Required default checks

| Check | Default handling |
|---|---|
| Entity and concept | Exact supplied IDs required; mismatch is NOT_COMPARABLE, missing is UNRESOLVED |
| Scope, population, denominator, granularity | Required by default; do not infer an unspecified population from equal numbers |
| Units | Registered equivalent dimensions convert exactly; incompatible dimensions do not compare; unknown units are unresolved |
| Time | Same explicit UTC window, or both explicitly timeless; differing aggregate windows are not interchangeable merely because they overlap |
| Numeric meaning | Both sides need an explicit numeric set; a missing meaning cannot become zero |
| Location / definition version | If declared on either side, require a match on both |
| Method | Recorded separately; distinct measurement methods are permitted unless the contract explicitly requires the same method |
| Dependence | Shared sources and missing dependence reported; not independent votes |

Default `require_time=True`. A caller can declare a static transaction/definition comparison as timeless. Do not use timeless to bypass a live-sensor freshness requirement.

Freshness is optional and explicit: supplying `max_age_seconds` requires an `as_of` timestamp. No ambient clock is used in deterministic replay. Stale or future-dated information under that contract is unresolved, not a physical contradiction.

## Partial and unknown alignment

Low confidence in an association is not numerical agreement. This release does not invent fuzzy entity equivalence, semantic similarity probabilities or automatic join confidence. An application can propose such an association, but must normalize the intended IDs and retain its attributed alignment support before the required deterministic checks run.

## Hinge orders

`PairSpec.hinge_orders` chooses examination levels for presentation and extension. It cannot disable required checks. `PairSpec.hinge_states` can attach `HingeOrderState(order, pd, support, note)` at any positive order. Missing declared higher-order support remains missing. These states are serialized with the pair, never with an independent H node.

## Extension contract

`HingeEvaluator.register_check(name, callable)` accepts trusted application code returning a uniquely named `HingeCheck`. It can add a failure or unknown; it cannot override required failures. Exceptions yield an UNKNOWN required check. An application that loads untrusted Python plugins does not gain a security boundary from this library.

## Outcomes

- ALIGNED: observed admissible set satisfies the expected set under the supplied contract.
- PARTIAL: comparable numeric sets overlap but do not establish containment.
- CONFLICT: comparable numeric sets are disjoint.
- UNRESOLVED: missing/unknown information prevents legitimate comparison.
- NOT_COMPARABLE: known subject, concept, scope or dimensional incompatibility.

NOT_COMPARABLE is deliberately not collapsed into CONFLICT, despite that conflation in one of the concept images. UNPAIRED is a matrix display state; UNMEASURED is an aggregate with no evaluations.
