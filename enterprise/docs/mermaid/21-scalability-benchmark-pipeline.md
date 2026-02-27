# Scalability Benchmark Pipeline

v2.0.8 CI-eligible benchmark producing scalability evidence, regression gate, and trend visualization.

```mermaid
flowchart TD
    subgraph Inputs["Benchmark Inputs"]
        DS["Synthetic dataset<br/>100K JSONL records"]
        CK["--ci-mode flag"]
        CP["Crypto policy<br/>governance/security_crypto_policy.json"]
    end

    subgraph Benchmark["reencrypt_benchmark.py"]
        CK --> ENV["Set env vars<br/>CRYPTO_POLICY_PATH<br/>kpi_eligible=true"]
        DS --> RJ["run_reencrypt_job()<br/>dry_run pipeline"]
        ENV --> RJ
        CP --> ENV
        RJ --> TEL["Telemetry collection<br/>wall clock, CPU, RSS, throughput"]
        TEL --> SCORE["_scalability_score()<br/>base(2) + MTTR(0-3)<br/>+ rps(0-3) + MB/min(0-2)"]
    end

    subgraph Outputs["Benchmark Outputs"]
        SCORE --> SM["scalability_metrics.json<br/>kpi_eligible: true<br/>evidence_level: real_workload"]
        SCORE --> SEC["security_metrics.json"]
        SCORE --> BH["benchmark_history.json<br/>append-only entries"]
        SCORE --> BS["benchmark_summary.json"]
    end

    subgraph Gate["Scalability Regression Gate"]
        BH --> SRG["scalability_regression_gate.py"]
        SRG --> C1{"throughput >= 80%<br/>of previous?"}
        SRG --> C2{"evidence_level is<br/>real_workload?"}
        C1 -->|PASS| SGR["SCALABILITY_GATE_REPORT.md"]
        C2 -->|PASS| SGR
        C1 -->|FAIL| FAIL["Gate FAIL<br/>exit 1"]
    end

    subgraph Trend["Benchmark Trend"]
        BH --> RT["render_benchmark_trend.py"]
        RT --> TP["benchmark_trend.png/svg<br/>throughput bar chart<br/>+ 80% floor line"]
        RT --> TM["benchmark_trend.md<br/>markdown history table"]
    end

    subgraph KPI["KPI Pipeline Integration"]
        SM --> KC["kpi_compute.py<br/>score_scalability()"]
        KC --> KM["kpi_merge.py<br/>eligibility tier: production"]
        KM --> MERGED["kpi_v2.0.8_merged.json<br/>scalability: 10.0"]
    end

    style Inputs fill:#16213e,stroke:#0f3460,color:#fff
    style Benchmark fill:#162447,stroke:#1f4068,color:#fff
    style Outputs fill:#0f3460,stroke:#533483,color:#fff
    style Gate fill:#533483,stroke:#e94560,color:#fff
    style Trend fill:#1a1a2e,stroke:#e94560,color:#fff
    style KPI fill:#e94560,stroke:#e94560,color:#fff
```

## Make Targets

| Target | What it does |
| --- | --- |
| `make benchmark` | Run benchmark with `--ci-mode` |
| `make scalability-gate` | Regression gate (80% floor) |
| `make benchmark-trend` | Render trend chart + table |
