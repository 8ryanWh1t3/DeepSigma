# Policy Packs

Policy Packs make enforcement **portable and auditable**.
Instead of embedding governance inside one framework, you ship it as a versioned bundle:

- `policyPackId` + `version`
- optional `signature`
- decisionType keyed rules:
  - DTE defaults
  - degrade ladder
  - blast radius requirements
  - required verifiers
  - tool allow/deny lists

See: `policy_packs/packs/demo_policy_pack_v1.json`
