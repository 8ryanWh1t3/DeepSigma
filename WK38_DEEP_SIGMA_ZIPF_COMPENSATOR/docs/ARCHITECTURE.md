# Architecture and integration boundaries

## Proposed Deep Sigma allocation

PATHFINDER supplies retrieved records and their provenance. RESONATOR hosts the frequency-aware attention calculation and contradiction review. COMPOSER receives governed change proposals. Claim, Event, Review, Patch and Apply (CERPA) supplies the surrounding lifecycle.

This ZIP implements a standalone evaluation slice, not those full systems. It does not change an existing Deep Sigma repository or establish that the prior ontology functions are implemented.

## Two independent decisions

1. Which claims should a reviewer see within a fixed discretionary budget?
2. Does a claim meet the supplied evidence and authority requirements for simulated verified release?

The scorer answers the first. The gate answers the second. A high score cannot satisfy missing evidence. A low score cannot suppress a mandatory alert. Gate checks run for every claim, including claims outside the attention shortlist.

## Determinism and parity

The core accepts all inputs explicitly, including scenario time, policy version and event provenance. Neither implementation calls a model, reads the clock or performs network I/O. Integer arithmetic, ASCII identifiers and deterministic tie-breaking keep the two implementations comparable. A JSON Schema is supplied for authoring assistance; each engine additionally checks cross-record invariants the schema cannot express.

The browser directly opens the supplied scripts in file mode. The local HTTP console calls the Python endpoint. The browser must not silently substitute a JavaScript result when a Python request fails. Both results remain simulations; server placement does not authenticate source facts or approval metadata.

## Evidence identity

Reports count distinct `(origin_id, event_id)` pairs after copies are collapsed. Reports and evidence use claim-specific event identities in this pilot. Evidence support counts distinct declared `origin_id` values; several independent events from one source still constitute one supporting origin. This distinction preserves recurrence without manufacturing corroboration.

Malformed inputs fail validation. An identified but inadequate claim produces an explicit HOLD. These are different conditions: bad JSON/schema means there is no evaluation result; absent qualifying evidence in a valid scenario means there is a result with reasons.

## Production work deliberately left explicit

The interface for future integration is `evaluate(payload)`. Replace scenario-provided identity, approval and policy assertions with records from trusted services. Bind approvals to an immutable content digest covering the exact claim, evidence set, policy and intended use. Re-check current revocation and freshness at every authorized use; persist decisions durably and propagate withdrawals to connected consumers. Add concurrency controls to prevent a claim changing between evaluation and use.

Semantic support assessment needs an accountable process. The `support_assessed` field is a fixture input, not an automated theorem that evidence entails the claim. A real assessor can still be wrong, and deceptive evidence can still pass a rule. Operational testing must evaluate those failure modes.

The server is a development utility bound to `127.0.0.1`. It serves only explicit assets, rejects unexpected hosts and cross-origin POSTs, limits request bodies, and does not write imports. It has no user authentication, TLS deployment, role directory or production audit store.

## Suggested next evaluation

Freeze the rule set and review budget. Hold truth labels outside the operator interface. Compare baseline attention, compensated attention and compensated attention with enforced release controls. Measure rare relevant recall, false positives, critical-alert retention, unnecessary holds, evidence-gap detection and correction propagation. The first three modes in this ZIP prepare that comparison; they do not establish real release enforcement.
