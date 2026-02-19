---
title: "MDPT Governance"
version: "0.6.3"
date: "2026-02-19"
---

# MDPT Governance

> How Multi-Dimensional Prompting for Teams maps to Coherence Ops on Power Platform.

---

## Coherence Ops Mapping

Every MDPT component has a direct equivalent in the Coherence Ops primitive model:

| MDPT Component | Coherence Ops Primitive | Artifact |
|----------------|------------------------|----------|
| PromptCapabilities list | Decision Scaffold (DS) | Templates for governed operations |
| PromptRuns list | Decision Ledger Record (DLR) | Sealed record of what was decided |
| DriftPatches list | Drift Signal + Patch Packet | Detection and correction |
| BOOT!A1 | Canon | Constitutional constraints |
| tblCanonGuardrails | Canon Guardrails | Hard constraints |
| tblClaims | Atomic Claims | Verifiable assertions |
| tblAssumptions | Reasoning Scaffold (RS) | Assumptions with half-life |
| CI_DASHBOARD | Coherence Score | Governance health metric |

---

## Permission Model

### SharePoint Site Permissions

| Role | SP Permission | Can Do |
|------|--------------|--------|
| Governance Admin | Site Owner | Create/modify lists, manage columns, configure flows |
| Team Lead | Site Member | Run prompts, create patches, approve patches |
| Team Member | Site Member | Run prompts, create drift signals |
| Viewer | Site Visitor | Read all lists, view dashboards |
| LLM Service | App-only (Graph API) | Read workbook, read lists (no write) |

### List-Level Permissions

| List | Create | Edit Own | Edit All | Approve |
|------|--------|----------|----------|---------|
| PromptCapabilities | Admin | Admin | Admin | — |
| PromptRuns | Member+ | Own items | Lead+ | — |
| DriftPatches | Member+ | Own items | Lead+ | Lead+ |

### Power App Roles

| App Role | Screens Accessible | Actions |
|----------|-------------------|---------|
| Admin | All | Full CRUD + config |
| Operator | All | Run prompts, manage patches |
| Viewer | Home, Prompt Gallery, Run Detail | Read-only |

---

## Audit Trail

### Three Layers of History

1. **SharePoint Version History** — every item edit is versioned automatically. Who changed what, when.
2. **Power Automate Run History** — every flow execution is logged with inputs, outputs, duration, and status.
3. **PromptRuns List** — explicit governance log of every LLM interaction with the workbook.

### What Gets Recorded

| Event | Where Recorded | Retention |
|-------|---------------|-----------|
| Prompt run executed | PromptRuns list | Permanent |
| Drift signal created | DriftPatches list | Permanent |
| Patch status changed | DriftPatches version history | Per SP retention policy |
| Approval granted/denied | Power Automate Approvals | 28 days (default) |
| Flow execution | Power Automate run history | 28 days (default) |
| Workbook edit | SP document version history | Per SP retention policy |

---

## Compliance Considerations

### Data Residency

All data stays within the Microsoft 365 tenant:
- SharePoint lists: tenant geography
- Power Automate: same region as tenant
- Power Apps: same region as tenant
- No external API calls required for core governance

### LLM Interaction Boundary

When users attach the workbook to an LLM:
- **ChatGPT / Claude**: Data leaves the tenant (user uploads file)
- **Copilot for M365**: Data stays within the tenant (Microsoft-managed)
- **Power Automate HTTP action**: Controlled by the endpoint target

Teams should document their LLM platform choice in the governance policy and ensure it meets their data classification requirements.

### Retention

- PromptRuns and DriftPatches lists follow the site's retention policy
- Recommend: minimum 2-year retention for governance audit trail
- Power Automate run history: extend via export to SharePoint list if needed

---

## Escalation Path

```
Team Member detects drift
    → DriftPatches: Open (auto-alert via Flow 1)
        → Team Lead triages (assigns severity)
            → Operator proposes patch
                → Team Lead approves (Flow 2)
                    → Patch applied + closed
                        → Weekly digest (Flow 3)

If SLA breached:
    → Auto-escalation to Governance Admin
        → If CRITICAL: VP notification
```

---

## See Also

- [Power Automate Flows](POWER_AUTOMATE_FLOWS.md)
- [Power Apps Screen Map](POWER_APPS_SCREEN_MAP.md)
- [PromptCapabilities Build Sheet](SHAREPOINT_LIST_BUILD_SHEET_PromptCapabilities.md)
- [Workbook Boot Protocol](../WORKBOOK_BOOT_PROTOCOL.md)
