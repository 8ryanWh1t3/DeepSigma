# Pilot DRI Model

## Required roles (minimum)
- **DLR Owner**: writes/maintains Decisions (DLR-*)
- **Truth Owner**: ensures evidence/provenance is attached
- **Coherence Steward**: runs drift triage weekly + enforces Patch cadence
- **Approver**: signs/approves patches for merges (branch protection)

## Cadence
- Daily: DLRs sealed + assumptions logged
- Weekly: drift triage + patch draft
- Monthly: patch release note + CI trend review

## Definition of Done
- Every DLR links ≥1 assumption
- Every drift links a patch reference (or an explicit waiver w/ rationale)
