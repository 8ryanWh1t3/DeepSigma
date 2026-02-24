from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module(repo_root: Path):
    mod_path = repo_root / "scripts" / "tec_estimate.py"
    spec = importlib.util.spec_from_file_location("tec_estimate", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_weights(path: Path) -> None:
    path.write_text(
        """
rates:
  internal_hourly: 150
  exec_hourly: 225
  dod_fully_burdened_hourly: 275
uncertainty:
  low: 0.8
  base: 1.0
  high: 1.35
issue_hours:
  type:feature: 8
  security_default: 12
  committee_cycle: 8
severity_multiplier:
  sev:P2: 1.0
complexity: {}
insights:
  enabled: true
  neutral_score: 5.0
  score_sensitivity: 0.02
  max_reduction: 0.12
  max_increase: 0.18
  signal_step: 0.015
  signal_cap: 0.12
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_insights_adjustment_reduces_hours_for_high_score(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    (repo / "governance").mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "scripts" / "tec_estimate.py"
    (repo / "scripts" / "tec_estimate.py").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    _write_weights(repo / "governance" / "tec_weights.yaml")

    module = _load_module(repo)
    adjusted, details = module._insights_adjustment(100.0, {"insights_score": 9.0, "signal_count": 0})
    assert adjusted < 100.0
    assert details["factor"] < 1.0


def test_insights_adjustment_increases_hours_for_low_score_and_signals(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    (repo / "governance").mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "scripts" / "tec_estimate.py"
    (repo / "scripts" / "tec_estimate.py").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    _write_weights(repo / "governance" / "tec_weights.yaml")

    module = _load_module(repo)
    adjusted, details = module._insights_adjustment(
        100.0, {"insights_score": 2.0, "signals": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}
    )
    assert adjusted > 100.0
    assert details["signal_count"] == 3
    assert details["factor"] > 1.0
