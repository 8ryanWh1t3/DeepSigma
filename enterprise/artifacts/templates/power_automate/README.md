# Power Automate Flow Templates — Prompt OS v2

Pre-built flow templates for automating the Prompt OS workbook lifecycle.

---

## Templates

| # | File | Trigger | Target Table | Purpose |
|---|------|---------|-------------|---------|
| 01 | `01_email_to_atomic_claims.json` | New email/Teams message | AtomicClaimsTable | Ingest claims from email |
| 02 | `02_meeting_notes_to_decision_log.json` | Manual button | DecisionLogTable | Capture decisions from meetings |
| 03 | `03_weekly_expiry_drift_flagging.json` | Weekly schedule (Mon 08:00) | PatchLogTable | Flag expired assumptions + degraded prompts |
| 04 | `04_export_sealed_snapshot.json` | Manual button | Archive (SharePoint) | Export sealed JSON + PDF snapshot |

---

## Import Instructions

1. Open [Power Automate](https://make.powerautomate.com)
2. Go to **My flows** → **Import** → **Import Package (Legacy)**
3. Select one of the `.json` files from this directory
4. Configure connections:
   - **Excel Online (Business)** — for workbook table access
   - **Office 365** — for email triggers and notifications
   - **Microsoft Teams** — for channel notifications
   - **SharePoint Online** — for archive storage (flow 04 only)
5. Replace placeholder values:
   - `{driveId}` — your OneDrive/SharePoint drive ID
   - `{fileId}` — your workbook file ID
   - `{tableId}` — target table ID (or use table name)
   - `{teamId}` / `{channelId}` — your notification channel
   - `{siteId}` — your SharePoint site (flow 04 only)
   - `@YOURDOMAIN.com` — your organization's email domain (flow 01)

---

## Configuration Notes

- **Default values**: Flows use sensible defaults (Confidence: 50, BlastRadius: 3, etc.) — operators adjust post-capture
- **Duplicate prevention**: Flow 03 checks for existing open patches before creating new ones
- **SHA-256 hashing**: Flow 04 includes a placeholder for seal hash computation. For production, wire in an Azure Function or HTTP action to a hashing service
- **Notification channels**: All flows send confirmations via Teams. Replace with email, Slack webhook, or other channels as needed
- **Table names**: Flows reference named tables (`DecisionLogTable`, `AtomicClaimsTable`, etc.) — ensure your workbook uses these exact names

---

## Related Docs

- [POWER_AUTOMATE_MAPPINGS.md](../../docs/prompt_os/POWER_AUTOMATE_MAPPINGS.md) — Detailed field mapping documentation
- [GOVERNANCE.md](../../docs/prompt_os/GOVERNANCE.md) — When to run each flow
