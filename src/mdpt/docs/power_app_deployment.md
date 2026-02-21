---
title: "MDPT Power App Deployment Guide"
version: "1.0"
date: "2026-02-20"
---

# MDPT Power App Deployment Guide

> Deploy the MDPT Prompt Operations app to a Power Platform environment.

---

## Overview

This guide walks through deploying the MDPT Power App package to a
Power Platform environment. The package includes:

- SharePoint list schemas (3 lists)
- Power App canvas app builder guide (8 screens)
- PowerFx code snippets (6 files)
- Power Automate flow template (scheduled index regeneration)
- Prompt index generator CLI tool

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| SharePoint Online | Any M365 tenant with a team site |
| Power Apps | Standard license (no premium connectors) |
| Power Automate | Standard license (Flow 4 requires Premium for HTTP) |
| Python 3.10+ | For CLI index generation only |

---

## Step 1: Create SharePoint Lists

Use the list schema in `sharepoint_list_schema.json` or build
manually from the build sheets.

### Option A: Manual Build (Recommended)

Follow the build sheets in order:

1. **PromptCapabilities** — 14 columns, 18 seed rows
   - See: `SHAREPOINT_LIST_BUILD_SHEET_PromptCapabilities.md`
2. **PromptRuns** — 15 columns
   - See: `SHAREPOINT_LIST_BUILD_SHEET_PromptRuns.md`
3. **DriftPatches** — 13 columns
   - See: `SHAREPOINT_LIST_BUILD_SHEET_DriftPatches.md`

### Option B: PnP Provisioning

If you have PnP PowerShell installed:

```powershell
# Connect to your SharePoint site
Connect-PnPOnline -Url https://contoso.sharepoint.com/sites/mdpt -Interactive

# Apply the schema (requires PnP site template conversion)
# The sharepoint_list_schema.json can be converted to a PnP template
# using the schema as a reference for column definitions.
```

### Verify Lists

After creation, confirm each list has:

- Correct column types (Choice, Lookup, DateTime, etc.)
- Default views configured
- At least 3 seed rows in PromptCapabilities

---

## Step 2: Seed PromptCapabilities

Add the 18 standard MDPT capabilities from the build sheet. These
cover all 6 lenses x 3 operations:

| Lens | IntelOps | ReOps | FranOps |
|------|----------|-------|---------|
| PRIME | Truth Standards Scan | Governance Invariant Check | Canon Precedence Lookup |
| EXEC | Top Claims + Blast Radius | Decision Gate Review | Narrative Risk Assessment |
| OPS | Collection Gap Analysis | Daily Loop Plan | Continuity Check |
| AI-TECH | Drift Automation Scan | Drift Trigger Review | Safe Summary Rules |
| HUMAN | Bias Risk Scan | Adoption Friction Review | Tone Guardrail Check |
| ICON | Truth Status Lights | Seal/Patch Marker Review | SEV Banner Audit |

---

## Step 3: Build the Power App

Follow the **Starter Kit** (`STARTER_KIT.md`) to build the 8-screen
canvas app. The kit provides:

- Screen-by-screen control layout tables
- PowerFx code for each interactive screen
- Data binding instructions
- Role-based visibility patterns

**Estimated build time:** 45-60 minutes for all 8 screens.

---

## Step 4: Import Power Automate Flow

Import the scheduled index regeneration flow:

1. Go to [make.powerautomate.com](https://make.powerautomate.com)
2. **My flows** > **Import** > **Import Package**
3. Upload `flow_scheduled_index_regen.json`
4. Configure connections:
   - SharePoint Online connection
   - Microsoft Teams connection
5. Set parameters:
   - `SharePointSiteUrl` — your site URL
   - `PromptCapabilitiesListId` — list GUID
   - `TeamsChannelId` — target channel for notifications
   - `TeamsTeamId` — team GUID
   - `IndexStorageFolder` — document library path
6. Save and enable the flow

The flow runs weekly (Monday 06:00 UTC) and:
- Exports active capabilities to CSV
- Computes index statistics
- Posts a summary to the Teams channel

---

## Step 5: Generate Prompt Index (CLI)

For offline or CI-driven index generation:

```bash
# Export PromptCapabilities to CSV from SharePoint
# (use the SharePoint UI: List > Export to CSV)

# Generate the index
python mdpt/tools/generate_prompt_index.py \
  --csv prompt_capabilities_export.csv \
  --out ./output/

# Outputs:
#   output/prompt_index.json        (schema-validated)
#   output/prompt_index_summary.md  (human-readable)
```

---

## Step 6: Verify Deployment

### Checklist

- [ ] All 3 SharePoint lists created with correct schemas
- [ ] PromptCapabilities seeded with 18 standard capabilities
- [ ] Power App opens and Catalog screen loads capabilities
- [ ] Can navigate through all 8 screens
- [ ] Can submit a prompt run from UseCapability screen
- [ ] Run appears in RunHistory after submission
- [ ] Can flag a drift signal from Evaluation screen
- [ ] Drift patch appears in Approvals queue
- [ ] Power Automate flow enabled and test-run succeeds
- [ ] Teams notification received on flow completion
- [ ] CLI index generator produces valid JSON output

### Smoke Test Flow

1. Open the Power App
2. Browse to a capability in Catalog
3. Launch a prompt run (UseCapability screen)
4. Submit findings with drift detected
5. Flag the drift (DriftReport screen)
6. Approve the patch (Approvals screen)
7. Check Teams channel for flow notification

---

## Package Contents

```
mdpt/
  docs/
    power_app_deployment.md        # This guide
  powerapps/
    STARTER_KIT.md                 # Screen-by-screen builder guide
    POWERAPPS_SCREEN_MAP.md        # Screen reference and data bindings
    sharepoint_list_schema.json    # Machine-readable list definitions
    flow_scheduled_index_regen.json # Power Automate flow template
    powerfx/
      catalog_gallery.pfx          # Catalog screen gallery logic
      filters_sort.pfx             # Filter and sort controls
      use_capability.pfx           # Capability launch logic
      submit_run.pfx               # Run submission with Patch()
      drift_report.pfx             # Drift signal creation
      approvals_queue.pfx          # Patch approval workflow
  templates/
    prompt_index_schema.json       # JSON Schema for index validation
  tools/
    generate_prompt_index.py       # CLI index generator
    package_power_app.py           # Package builder (.zip)
```

---

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Gallery shows no items | Check SharePoint connection in Data panel |
| Lookup column errors | Ensure PromptCapabilities list is created first |
| Flow fails on Teams post | Verify Teams connection and channel permissions |
| Index generator schema error | Ensure CSV has all required columns |
| Permission denied on list | Check item-level permissions in list settings |

---

## See Also

- [Starter Kit](../powerapps/STARTER_KIT.md)
- [Screen Map](../powerapps/POWERAPPS_SCREEN_MAP.md)
- [Power Automate Flows](../../docs/excel-first/multi-dim-prompting-for-teams/POWER_AUTOMATE_FLOWS.md)
- [SharePoint Build Sheets](../../docs/excel-first/multi-dim-prompting-for-teams/)
