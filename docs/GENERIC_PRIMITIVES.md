# Generic Primitive Enforcement (GPE)

## GPR-1: Generic Primitive Rule
1) No proper nouns. Ever.
2) Only three semantic layers: Actors, Artifacts, Events.
3) Scenarios must be industry-agnostic incidents.
4) Replace identifiers with tokens (OrgA, PolicyOffice, SystemX, PersonA, Policy-001).
5) No sector-specific jargon or metrics.
6) Enforcement: forbidden terms must be zero.

## GPE-Strict
- Denylist scan (hard fail everywhere)
- Heuristic scan (proper noun / domain leaks) (hard fail)
- Heuristics ignore fenced code blocks (so docs/code examples don't spam false positives)
- Optional auto-fix: `python scripts/domain_scrub.py --fix`

## Definition of Done
- `domain_scrub` CI check passes.
- Forbidden terms count == 0.
- Heuristic flags are either fixed or explicitly allowlisted.
