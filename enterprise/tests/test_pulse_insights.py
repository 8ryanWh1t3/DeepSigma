from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module(repo_root: Path):
    mod_path = repo_root / "scripts" / "pulse_insights.py"
    spec = importlib.util.spec_from_file_location("pulse_insights", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pulse_insights_writes_metrics_file(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    (repo / "release_kpis").mkdir(parents=True, exist_ok=True)

    source = Path(__file__).resolve().parents[1] / "scripts" / "pulse_insights.py"
    (repo / "scripts" / "pulse_insights.py").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    release_kpis = repo / "release_kpis"
    output = release_kpis / "insights_metrics.json"
    (release_kpis / "VERSION.txt").write_text("v2.0.6\n", encoding="utf-8")
    (release_kpis / "issue_deltas.json").write_text(
        json.dumps(
            {
                "kpis": {
                    "automation_depth": {
                        "open_count": 4,
                        "closed_since_count": 3,
                        "credit_delta": 2.2,
                        "debt_delta": 0.5,
                        "cap_if_open_p0": None,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (release_kpis / "kpi_v2.0.6_merged.json").write_text(
        json.dumps(
            {
                "values": {
                    "technical_completeness": 7.1,
                    "automation_depth": 6.8,
                    "authority_modeling": 6.2,
                    "enterprise_readiness": 6.0,
                    "scalability": 6.1,
                    "data_integration": 6.4,
                    "economic_measurability": 5.9,
                    "operational_maturity": 6.5,
                }
            }
        ),
        encoding="utf-8",
    )
    (release_kpis / "history.json").write_text(
        json.dumps(
            {
                "entries": [
                    {"version": "v2.0.5", "values": {"automation_depth": 6.0}},
                    {"version": "v2.0.6", "values": {"automation_depth": 6.8}},
                ]
            }
        ),
        encoding="utf-8",
    )

    module = _load_module(repo)
    module.ROOT = repo
    module.OUT = repo / "release_kpis"
    assert module.main() == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "pulse_insights_v1"
    assert payload["source"] == "pulse"
    assert isinstance(payload["insights_score"], (int, float))
    assert "signals" in payload
    assert payload["inputs"]["issue_deltas_present"] is True
