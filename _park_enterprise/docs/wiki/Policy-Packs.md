# Policy Packs

Policy Packs package enforcement as a versioned artifact:
- `policyPackId`, `version`, `policyPackHash`
- decisionType keyed rules:
  - DTE defaults
  - degrade ladder
  - blast radius requirements
  - required verifiers
  - tool allow/deny lists

File location:
- `policy_packs/packs/demo_policy_pack_v1.json`

Why it matters:
- governance becomes portable across environments
- sealed episodes record which policy governed the run
