from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module(repo_root: Path):
    mod_path = repo_root / "scripts" / "kpi_compute.py"
    spec = importlib.util.spec_from_file_location("kpi_compute", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_score_economic_measurability_from_metrics(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "scripts" / "kpi_compute.py"
    (repo / "scripts" / "kpi_compute.py").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "release_kpis").mkdir(parents=True, exist_ok=True)
    (repo / "release_kpis" / "security_metrics.json").write_text(
        json.dumps(
            {
                "mttr_seconds": 120,
                "reencrypt_records_per_second": 5,
                "reencrypt_mb_per_minute": 0.1,
                "kpi_eligible": True,
                "evidence_level": "real_workload",
            }
        ),
        encoding="utf-8",
    )

    module = _load_module(repo)
    module.ROOT = repo

    metrics = module.parse_security_metrics()
    assert metrics is not None
    score = module.score_economic_measurability(metrics)
    assert score >= 8


def test_score_economic_measurability_is_capped_for_simulated_metrics(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "scripts" / "kpi_compute.py"
    (repo / "scripts" / "kpi_compute.py").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "release_kpis").mkdir(parents=True, exist_ok=True)
    (repo / "release_kpis" / "security_metrics.json").write_text(
        json.dumps(
            {
                "mttr_seconds": 1,
                "reencrypt_records_per_second": 999999,
                "reencrypt_mb_per_minute": 999999,
                "kpi_eligible": False,
                "evidence_level": "simulated",
            }
        ),
        encoding="utf-8",
    )

    module = _load_module(repo)
    module.ROOT = repo
    metrics = module.parse_security_metrics()
    assert metrics is not None
    assert module.score_economic_measurability(metrics) <= 4.0


def test_main_omits_economic_measurability_without_metrics(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "scripts" / "kpi_compute.py"
    (repo / "scripts" / "kpi_compute.py").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    module = _load_module(repo)
    module.ROOT = repo

    payload = json.loads(__import__("subprocess").check_output(["python", str(repo / "scripts" / "kpi_compute.py")], text=True))
    assert "economic_measurability" not in payload
