# Glossary

- **RAL**: Reality Await Layer (“await for reality”)
- **DTE**: Decision Timing Envelope (time budgets)
- **TTL/TOCTOU**: freshness gating and time-of-check/time-of-use risk
- **Safe Action Contract**: blast radius + idempotency + rollback + auth
- **DecisionEpisode**: sealed audit unit
- **DriftEvent**: structured variance/failure signal that triggers patching
- **SSI**: System Stability Index — 0-100 composite detecting unsustainable KPI swings (volatility 35%, drift acceleration 30%, authority 20%, economic 15%)
- **TEC Sensitivity**: Economic fragility analysis measuring C-TEC cost impact when RCF/CCF shift by one tier
- **Security Proof Pack**: Integrity-chain-aware security gate checking key lifecycle, crypto proof, seal chain, and contract fingerprint
- **Kill-Switch**: Stale artifact gate validating version match, radar existence, badge freshness, history, and contract fingerprint before release
- **KPI Eligibility Tier**: Evidence-based score cap — unverified (3.0), simulated (6.0), real (8.5), production (10.0)
- **Drift Acceleration**: Second derivative of KPI movements across releases; high values indicate unsustainable change velocity
- **CI-Eligible Evidence**: Benchmark output produced with `--ci-mode` that sets `kpi_eligible=true` and `evidence_level=real_workload`, uncapping telemetry-derived KPI scores from the 4.0 simulated ceiling
- **Scalability Regression Gate**: CI gate preventing throughput regressions — enforces 80% throughput floor vs. previous benchmark and requires real_workload evidence level
- **Benchmark Trend**: Historical throughput visualization from `benchmark_history.json` showing records/sec over time with 80% regression floor overlay
