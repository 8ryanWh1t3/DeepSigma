# SharePoint Connector Contract (Public-Safe Template)

This document is intentionally generic. Do not include internal site names, tenant IDs,
customer identifiers, or restricted paths.

## Inputs
- Item list endpoint
- Item metadata
- Document download or URL reference

## Required Fields (Minimum)
- `item_id` (string)
- `title` (string)
- `url` (string)
- `modified_utc` (ISO 8601)
- `owner` (string, optional)
- `tags` (string, optional)

## Output
- Turtle `.ttl` triples aligned to `ontology/coherence_ops.ttl`
- Optional: CSV audit trail of extracted entities

## Security Notes
- Principle: SharePoint holds blobs; graph holds meaning.
- Never embed full document content into public repos.
- Keep extraction artifacts abstracted and sanitized.
