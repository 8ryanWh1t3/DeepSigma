# AuthorityOps Enterprise Adapters

Extension points for integrating external identity, policy, approval, audit, and kill-switch systems into the AuthorityOps evaluation pipeline.

## Contracts

| Interface | Target Systems | AuthorityOps Handler |
|-----------|---------------|---------------------|
| `IdentityProviderV1` | Entra ID, Okta, LDAP | AUTH-F02 (Actor Resolution) |
| `PolicyStoreV1` | OPA, Cedar, custom policy DBs | AUTH-F04 (Policy Load) |
| `ApprovalSystemV1` | Jira, ServiceNow, PagerDuty | AUTH-F10 (Decision Gate — ESCALATE path) |
| `AuditSinkV1` | Splunk, Elastic, Datadog, S3 | AUTH-F11 (Audit Record Emit) |
| `KillSwitchProviderV1` | LaunchDarkly, PagerDuty, custom | AUTH-F09 (Kill Switch Check) |

## Implementation Guide

1. Implement the Protocol interface in `contracts.py`
2. Register the adapter in the enterprise adapter registry
3. Configure via environment or YAML config
4. The AuthorityOps runtime will call through the protocol at evaluation time

## Not Yet Implemented

These are interface contracts only. Full connector implementations are planned for:

- **Entra ID / Azure AD** — `IdentityProviderV1`
- **Okta** — `IdentityProviderV1`
- **GitHub** — `IdentityProviderV1` (org/team roles)
- **SharePoint** — `PolicyStoreV1` (document-level governance)
- **Jira** — `ApprovalSystemV1`
- **CI/CD Pipelines** — `KillSwitchProviderV1` (deploy gates)
- **Kubernetes** — `KillSwitchProviderV1` (admission control)
