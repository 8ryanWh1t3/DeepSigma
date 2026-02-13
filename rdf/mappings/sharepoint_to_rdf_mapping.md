# SharePoint → RDF Mapping (v0.1)

Goal: demote SharePoint to **blob storage** while promoting the **graph** as the system of record
for Coherence Ops Truth · Reasoning · Memory.

## Canonical Mappings

| SharePoint Concept | RDF Concept |
|---|---|
| Document (file) | `:Source` |
| Document URL | `:hasBlobLocation` |
| Metadata column | predicate (datatype or object property) |
| Approval workflow | `:Actor` + `:Authority` relationships (future expansion) |
| Version history | `:supersedes` chains (for `:Patch` or `:Source` versions) |
| Folder path / library | `:Domain` tag |

## Suggested Extraction Targets
- `:Claim` (atomic, testable statement)
- `:Evidence` (what supports the claim)
- `:Source` (doc, policy, dataset, email, meeting record)
- `:Decision` (the committed choice)
- `:Assumption` (with expiry and half-life)
- `:DriftEvent` (contradiction, mismatch, unexpected outcome)
- `:Patch` (resolution artifact)

## Minimal Output
- Turtle (`.ttl`) for graph ingestion
- CSV export for audit trail (optional)

See `sample_sharepoint_export.csv` and `sample_rdf_output.ttl` for a toy example.
