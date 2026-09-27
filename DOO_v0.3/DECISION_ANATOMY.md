# DOO Decision Anatomy

A portable decision should answer a stable set of semantic questions even when it moves between platforms.

| Question | DOO representation |
|---|---|
| What problem was being solved? | `DecisionProblem` + `addressesProblem` |
| What context mattered? | `DecisionContext` |
| What options existed? | `DecisionOption` |
| What was selected/rejected? | `selectsOption` / `rejectsOption` |
| Who or what made the decision? | `madeBy` |
| Why? | `whySummary` + `DecisionRationale` |
| What evidence supported it? | `Claim` → `supportedBy` → `Evidence` |
| What assumptions carried it? | `Assumption` |
| What was expected to happen? | `ExpectedOutcome` + `anticipatesOutcome` |
| What risks/tradeoffs/dependencies existed? | `Risk`, `Tradeoff`, `Dependency` |
| What authority applied? | `Authority`, `Approval`, `PolicyBasis` |
| What happened next? | `Action` → `Outcome` |
| What changed afterward? | `Review`, `DriftSignal`, `Patch`, `supersedes` |
| What survives for future users/systems? | `DecisionLineageRecord`, `DecisionPacket`, PROV-O |

The minimal interoperability contract is not that every field must be populated. It is that implementations preserve **identity, distinctions, and relationships** for the profile they claim.
