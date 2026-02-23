# Data Boundaries

This page defines how DeepSigma handles data for connector-based ingestion and pilot operations.
It is designed for enterprise security review and intentionally excludes any real secrets, tenant IDs, or endpoint URLs.

## Data At Rest

DeepSigma stores only operational artifacts required for governance and replay:
- JSONL evidence/event logs
- Sealed packets and report outputs
- Audit logs and scorecard outputs
- Tenant-scoped runtime configuration metadata

The platform does not require raw source-system data dumps by default. Connectors should normalize minimally and preserve provenance metadata.

## Storage Locations

Default storage is local filesystem:
- Tenant data root: `data/credibility/{tenant_id}/`
- Pilot artifacts and reports: `pilot/`, `artifacts/`, `release_kpis/`
- Temporary processing files: OS temp directories and explicit run output folders

Cloud storage is not enabled by default. Any external persistence must be explicitly configured by deployers.

## Retention

Retention follows TTL-based tiering and compaction patterns:
- Hot tier: recent evidence required for active drift detection and patch cycles
- Warm tier: sealed historical artifacts retained for replay/audit windows
- Cold tier: long-term, low-access archival artifacts

Compaction and retention sweeps are performed with explicit commands/workflows (for example retention sweep jobs), not implicit deletion.

## Redaction

Redaction is connector-first:
- Strip or mask PII before writing records into evidence pipelines
- Preserve structural fields needed for traceability (record IDs, source markers, timestamps)
- Replace sensitive payload fields with deterministic placeholders where needed

Guideline: if a source field is not required for decision governance, do not ingest it.

## Tenancy Separation

Tenancy isolation is enforced by design constraints:
- Per-tenant storage directories (`data/credibility/{tenant_id}/...`)
- Tenant context passed through runtime APIs and policies
- No intentional cross-tenant joins in default flows
- RBAC/tenant headers must be enforced at service boundaries in deployed environments

Any shared infrastructure deployment must preserve tenant partitioning at storage and API layers.

## Connector Data Flow

Connectors are read-oriented ingestion adapters. Typical sources:
- SharePoint (document/content retrieval)
- Snowflake (query/read access)
- Dataverse / Power Platform (entity/read access)

Default behavior is read-only. No write-back to source systems is required for core drift and patch workflows.

## Secrets Management

Secrets handling rules:
- Use environment variables or secret managers in deployment environments
- Never commit secrets to source code, fixtures, templates, or config files
- Avoid embedding credentials in command history, logs, or generated artifacts

Repository policy: no hardcoded secrets in code or docs.

## Network Boundaries

Outbound network calls depend on enabled adapters and may include:
- Microsoft Graph API (for SharePoint-class connectors)
- Snowflake service endpoints (for Snowflake connectors)
- AskSage API endpoints (for AskSage adapters)

No external endpoint is contacted unless that connector or workflow is explicitly invoked and configured.

## Security Review Checklist

- Data paths are tenant-scoped
- Connectors default to read-only behavior
- Redaction is applied before persistence
- Retention uses explicit TTL/compaction controls
- Secrets are provided at runtime, not stored in repo artifacts
