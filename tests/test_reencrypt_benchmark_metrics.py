from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess


def _load_kpi_compute(repo_root: Path):
    mod_path = repo_root / "scripts" / "kpi_compute.py"
    spec = importlib.util.spec_from_file_location("kpi_compute", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reencrypt_benchmark_writes_scalability_metrics(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = tmp_path / "bench"
    metrics_path = tmp_path / "scalability_metrics.json"
    summary_path = tmp_path / "summary.json"

    cmd = [
        "python",
        str(repo_root / "scripts" / "reencrypt_benchmark.py"),
        "--records",
        "1000",
        "--dataset-dir",
        str(out_dir),
        "--checkpoint",
        str(tmp_path / "checkpoint.json"),
        "--metrics-out",
        str(metrics_path),
        "--summary-out",
        str(summary_path),
        "--reset-dataset",
    ]
    subprocess.check_call(cmd, cwd=repo_root)

    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["records_targeted"] == 1000
    assert metrics["throughput_records_per_second"] > 0
    assert metrics["rss_peak_bytes"] > 0
    assert metrics["execution_mode"] == "dry_run"
    assert metrics["evidence_level"] == "simulated"
    assert metrics["kpi_eligible"] is False


def test_kpi_compute_supports_scalability_metrics(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "scripts" / "kpi_compute.py"
    (repo / "scripts" / "kpi_compute.py").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "release_kpis").mkdir(parents=True, exist_ok=True)
    (repo / "release_kpis" / "scalability_metrics.json").write_text(
        json.dumps({"scalability_score": 7.4, "kpi_eligible": True, "evidence_level": "real_workload"}),
        encoding="utf-8",
    )

    module = _load_kpi_compute(repo)
    module.ROOT = repo
    metrics = module.parse_scalability_metrics()
    assert metrics is not None
    assert module.score_scalability(metrics) == 7.4


def test_kpi_compute_caps_simulated_scalability_metrics(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "scripts" / "kpi_compute.py"
    (repo / "scripts" / "kpi_compute.py").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "release_kpis").mkdir(parents=True, exist_ok=True)
    (repo / "release_kpis" / "scalability_metrics.json").write_text(
        json.dumps({"scalability_score": 9.8, "kpi_eligible": False, "evidence_level": "simulated"}),
        encoding="utf-8",
    )

    module = _load_kpi_compute(repo)
    module.ROOT = repo
    metrics = module.parse_scalability_metrics()
    assert metrics is not None
    assert module.score_scalability(metrics) <= 4.0
