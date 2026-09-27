# Gray Zone Pattern Assessment

Assessment: `assessment-dd2335d20392b65c`
Window: 2026-08-19 13:50:00+00:00 to 2026-09-18 13:50:00+00:00
Observations: 4 · Links: 3 · Candidates: 1

## Candidate patterns

### hyp-cbfd923415a5 · priority 92/100 · unreviewed

Possible related pattern across observations; coordination remains unproven.

Evidence event IDs: `obs-001`, `obs-002`, `obs-003`
Source lineage groups: collection-1, collection-2, collection-3

Competing explanations:
- Routine operations, maintenance, training or environmental conditions — Check: Compare approved activity schedule and ordinary-rate baseline for the same period.
- Common upstream feed or duplicate reporting makes events appear independent — Check: Trace record identifiers and lineage groups to the original collection path.
- Unrelated events share a label, entity alias or broad location — Check: Verify entity resolution and seek discriminating observations across sources.

Collection gaps:
- Establish an ordinary-rate baseline before interpreting recurrence.
- Validate source independence and original record lineage.
- Seek disconfirming observations for each competing explanation.

## Observations and provenance

| Event | Time (UTC) | Channel | Source record / SHA-256 | Summary |
|---|---|---|---|---|
| obs-001 | 2026-09-18T13:00:00+00:00 | sensor | sensor-A/a-001 @ synthetic_cuas.lattice.jsonl:1 (7e4d3158a5568e6a3b63b8e8cd1d36dc6ce64e6917373572bab7ea3e74c7c47d) | Unidentified track observed in exercise sector A. |
| obs-002 | 2026-09-18T13:20:00+00:00 | human_report | observer-B/b-002 @ synthetic_cuas.lattice.jsonl:2 (b776ec2184b560f7fbc5d3381a350013139eceab4ad655aebbef7e8bd5158cff) | Operator independently reported track-17 in exercise sector A. |
| obs-003 | 2026-09-18T13:42:00+00:00 | spectrum | spectrum-C/c-003 @ synthetic_cuas.lattice.jsonl:3 (464e4990bd131c26bf39dcea6ac11fb40871f73416c5012c657389570ec0f665) | Exercise spectrum log contains a record associated with track-17. |
| obs-004 | 2026-09-18T13:50:00+00:00 | maintenance | maintenance-D/d-004 @ synthetic_cuas.lattice.jsonl:4 (d72261b4d1a178626260162f923ce5f50b9101774e52981604fb2aaa405c4518) | Scheduled diagnostic in exercise sector A. |

## Limits

- Priority score is a deterministic review order, not a probability or intent assessment.
- A candidate pattern does not establish coordination, actor identity, or hostility.
- Completeness depends on the supplied feeds, source lineage, identifiers, and baseline.
