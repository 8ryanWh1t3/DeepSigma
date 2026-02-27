# Authority + Economic Evidence Pipeline

v2.0.9 authority custody, refusal contracts, evidence chain export, and economic metrics uncapping.

```mermaid
flowchart TD
    subgraph Authority["Authority Track"]
        KC["KEY_CUSTODY.md<br/>generation + rotation + revocation"]
        CP["security_crypto_policy.json<br/>HMAC-SHA256, 90-day rotation"]
        AL["authority_ledger.py<br/>signing_key_id tracking"]
        KC --> AL
        CP --> AL

        RC["action_contract.py<br/>REFUSE action type"]
        RC --> RL["authority_ledger.py<br/>AUTHORITY_REFUSAL entries"]
        RL --> AG["authority_gate.py<br/>AUTHORITY_REFUSED drift signal"]

        AL --> EXP["export_authority_evidence.py"]
        RL --> EXP
        EXP --> AE["authority_evidence.json<br/>chain_verified, grant/refusal counts<br/>signing_key_ids, verification_hash"]
    end

    subgraph Economic["Economic Track"]
        TEC["tec_internal.json<br/>hours, costs"]
        SEC["security_metrics.json<br/>MTTR, rps, MB/min"]
        ISS["issues_all.json<br/>decision count"]
        TEC --> EM["economic_metrics.py"]
        SEC --> EM
        ISS --> EM
        EM --> EMJ["economic_metrics.json<br/>kpi_eligible: true<br/>evidence_level: real_workload"]
    end

    subgraph KPI["KPI Pipeline Integration"]
        AE --> KFC["kpi_compute.py<br/>score_authority_modeling()"]
        EMJ --> KFC2["kpi_compute.py<br/>score_economic_measurability()"]
        KFC --> MRG["kpi_merge.py"]
        KFC2 --> MRG
        MRG --> MERGED["kpi_v2.0.9_merged.json<br/>authority: 9.72<br/>economic: 10.0<br/>all 8 KPIs >= 7.0"]
    end

    subgraph Issues["Issue Resolution"]
        I413["#413 Key Custody"] -->|closed| P0
        I414["#414 Refusal Contract"] -->|closed| P0
        I415["#415 Evidence Export"] -->|closed| P0
        P0["#325 P0 Authority-Bound<br/>Action Contracts"] -->|closed| CAP["cap_if_open_p0: null<br/>authority uncapped"]
        I404["#404 Cost Ledger"] -->|closed| ECON
        I405["#405 Value Delta"] -->|closed| ECON
        I406["#406 Ingestion Gate"] -->|closed| ECON["economic_measurability<br/>uncapped 4.88 → 10.0"]
    end

    style Authority fill:#16213e,stroke:#0f3460,color:#fff
    style Economic fill:#162447,stroke:#1f4068,color:#fff
    style KPI fill:#e94560,stroke:#e94560,color:#fff
    style Issues fill:#533483,stroke:#e94560,color:#fff
```

## Make Targets

| Target | What it does |
| --- | --- |
| `make authority-evidence` | Export authority evidence chain |
| `make economic-metrics` | Generate economic_metrics.json |
| `make kpi` | Full KPI pipeline (includes both) |
