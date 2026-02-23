# C-TEC Pipeline (v1.0)

Complexity-Weighted TEC (C-TEC) derives Time/Effort/Cost from deterministic repo telemetry and publishes three lenses: Internal, Executive, and DoD.

```mermaid
flowchart TD
    subgraph Inputs["Repo Telemetry Inputs"]
        I1["Issues (type, sev, labels, duration, refs)"]
        I2["Merged PRs (additions, deletions, changed files)"]
        I3["Repo Surface (workflows, tests, docs)"]
    end

    subgraph Base["Base Effort Model"]
        B1["Type Hours"]
        B2["Severity Multiplier"]
        B3["Security Floor"]
        B4["Committee Cycle Hours"]
        B5["PR Overhead + Repo Surface Hours"]
        B6["Base Hours"]
    end

    subgraph Complexity["Complexity Index (C-TEC v1.0)"]
        C1["PR Diff Complexity"]
        C2["Cross-Subsystem Touch"]
        C3["Duration Multiplier"]
        C4["Dependency/Reference Multiplier"]
        C5["Complexity Index"]
    end

    subgraph Outputs["Tiered Outputs"]
        O1["Internal ROM"]
        O2["Executive ROM"]
        O3["DoD ROM"]
        O4["TEC_SUMMARY.md"]
        O5["PR_COMMENT.md TEC block"]
    end

    I1 --> B1
    I1 --> B2
    I1 --> B3
    I1 --> B4
    I2 --> B5
    I3 --> B5

    B1 --> B6
    B2 --> B6
    B3 --> B6
    B4 --> B6
    B5 --> B6

    I2 --> C1
    I1 --> C2
    I1 --> C3
    I1 --> C4
    C1 --> C5
    C2 --> C5
    C3 --> C5
    C4 --> C5

    B6 --> O1
    C5 --> O1
    B6 --> O2
    C5 --> O2
    B6 --> O3
    C5 --> O3
    O1 --> O4
    O2 --> O4
    O3 --> O4
    O4 --> O5
```

## Formula

```text
Effective_Hours = Base_Hours + (Issue_Base_Hours * Complexity_Index_Adjustment)
```

Where complexity adjustment is derived from PR churn, subsystem spread, issue duration, and coordination references.
