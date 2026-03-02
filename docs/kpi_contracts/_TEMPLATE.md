# KPI Contract: {KPI_NAME}

| Field | Value |
|-------|-------|
| **KPI_ID** | DS-KPI-{NNN} |
| **KPI_VERSION** | 1.0 |
| **Status** | Active / Experimental |
| **Owner** | Maintainer (DRI) |

## Intent

What decision does this KPI support?

## Formula

```
score = ...
```

Plain-English: ...

## Inputs / Data Sources

| Input | Path | Type |
|-------|------|------|
| ... | `path/to/source` | telemetry / manual / CI artifact |

## Cadence

How often is this KPI recomputed? (e.g., every release, per-episode)

## Thresholds

| Level | Condition | Action |
|-------|-----------|--------|
| Green | score >= X | No action |
| Yellow | X > score >= Y | Review at next release |
| Red | score < Y | Release blocked; remediation required |

**Floor:** minimum acceptable value (from `kpi_spec.yaml`)
**Max drop:** maximum release-to-release regression allowed

## Failure Modes / Gaming Risks

- What could cause a false-high score?
- What could cause a false-low score?
- How might this KPI be gamed?

## Standards Overlay

| Standard | Mapping |
|----------|---------|
| DORA | ... |
| ISO/IEC 25010 | ... |
| OTel | ... |
| SMART | S:_ · M:_ · A:_ · R:_ · T:_ · Net: _ |

## Change History

| Date | Version | Change |
|------|---------|--------|
| YYYY-MM-DD | 1.0 | Initial contract |
