# Pilot DRI Model

## Required roles (minimum)
- DLR Owner: writes and maintains Decisions (`DLR-*`)
- Truth Owner: ensures evidence and provenance are attached
- Coherence Steward: runs drift triage weekly and enforces patch cadence
- Approver: signs patches for merges (branch protection)

## Cadence
- Daily: new DLRs sealed and assumptions recorded
- Weekly: drift triage and patch draft
- Monthly: patch release note and CI trend review

## Definition of Done
- Every DLR links >=1 assumption
- Every drift has a patch reference (or explicitly waived with rationale)
