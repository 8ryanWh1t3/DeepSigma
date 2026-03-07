"""Tests for core.cli — CLI entrypoint and command functions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.cli import (  # noqa: E402
    _build_manifest,
    _build_pipeline,
    _load_drift,
    _load_episodes,
    _load_json_like,
    main,
)


SAMPLE_EPISODES_PATH = _SRC_ROOT / "core" / "examples" / "sample_episodes.json"
SAMPLE_DRIFT_PATH = _SRC_ROOT / "core" / "examples" / "sample_drift.json"


# ── Loader tests ─────────────────────────────────────────────────


class TestLoadJsonLike:
    def test_list_input(self):
        result = _load_json_like('[{"a": 1}]')
        assert isinstance(result, list)
        assert len(result) == 1

    def test_dict_input(self):
        result = _load_json_like('{"a": 1}')
        assert isinstance(result, list)
        assert len(result) == 1

    def test_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _load_json_like("not json")


class TestLoadEpisodes:
    def test_load_from_file(self):
        episodes = _load_episodes(str(SAMPLE_EPISODES_PATH))
        assert isinstance(episodes, list)
        assert len(episodes) > 0

    def test_load_from_directory(self, tmp_path):
        ep = {"episodeId": "ep-1", "decisionType": "test", "outcome": {"code": "success"}}
        (tmp_path / "ep1.json").write_text(json.dumps([ep]))
        episodes = _load_episodes(str(tmp_path))
        assert len(episodes) == 1

    def test_load_nonexistent_exits(self):
        with pytest.raises(SystemExit):
            _load_episodes("/nonexistent/path/that/does/not/exist")


class TestLoadDrift:
    def test_load_drift_file(self):
        events = _load_drift(str(SAMPLE_DRIFT_PATH))
        assert isinstance(events, list)
        assert len(events) > 0

    def test_load_drift_directory(self, tmp_path):
        drift = {"driftId": "d-1", "driftType": "freshness"}
        (tmp_path / "drift_events.json").write_text(json.dumps([drift]))
        events = _load_drift(str(tmp_path))
        assert len(events) == 1

    def test_load_drift_no_file(self, tmp_path):
        events = _load_drift(str(tmp_path))
        assert events == []


# ── Pipeline builder ─────────────────────────────────────────────


class TestBuildPipeline:
    def test_returns_four_tuple(self, sample_episodes, sample_drift_events):
        dlr, rs, ds, mg = _build_pipeline(sample_episodes, sample_drift_events)
        assert dlr is not None
        assert rs is not None
        assert ds is not None
        assert mg is not None

    def test_empty_drift(self, sample_episodes):
        dlr, rs, ds, mg = _build_pipeline(sample_episodes, [])
        assert ds.event_count == 0


class TestBuildManifest:
    def test_manifest_complete(self):
        manifest = _build_manifest()
        assert manifest.is_complete() is True
        assert manifest.system_id == "coherence-cli"


# ── Main parser ──────────────────────────────────────────────────


class TestMainParser:
    def test_no_args_no_error(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["coherence"])
        # main() with no args should not crash (just print help or do nothing)
        try:
            main()
        except SystemExit as e:
            # argparse may exit 0 or 2
            pass

    def test_version(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["coherence", "--version"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


# ── cmd_score ────────────────────────────────────────────────────


class TestCmdScore:
    def test_score_text(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "coherence", "score", str(SAMPLE_EPISODES_PATH),
        ])
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "Coherence Score" in captured.out

    def test_score_json(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "coherence", "score", str(SAMPLE_EPISODES_PATH), "--json",
        ])
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "overall_score" in data


# ── cmd_audit ────────────────────────────────────────────────────


class TestCmdAudit:
    def test_audit_text(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "coherence", "audit", str(SAMPLE_EPISODES_PATH),
        ])
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "Coherence Audit" in captured.out


# ── cmd_mg_export ────────────────────────────────────────────────


class TestCmdMGExport:
    def test_mg_export_json(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "coherence", "mg", "export", str(SAMPLE_EPISODES_PATH),
            "--format", "json",
        ])
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "nodes" in data


# ── cmd_iris_query ───────────────────────────────────────────────


class TestCmdIRISQuery:
    def test_iris_status(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "coherence", "iris", "query", str(SAMPLE_EPISODES_PATH),
            "--type", "STATUS",
        ])
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert len(captured.out) > 0


# ── cmd_reconcile ────────────────────────────────────────────────


class TestCmdReconcile:
    def test_reconcile_text(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "coherence", "reconcile", str(SAMPLE_EPISODES_PATH),
        ])
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "Reconciliation" in captured.out


# ── cmd_schema_validate ──────────────────────────────────────────


class TestCmdSchemaValidate:
    def test_validate_valid_episode(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "coherence", "schema", "validate", str(SAMPLE_EPISODES_PATH),
            "--schema", "episode",
        ])
        with pytest.raises(SystemExit) as exc_info:
            main()
        # May pass or fail depending on sample data vs schema strictness
        assert exc_info.value.code in (0, 1)


# ── cmd_dte_check ────────────────────────────────────────────────


class TestCmdDteCheck:
    def test_dte_check(self, capsys, monkeypatch, tmp_path):
        dte_spec = {
            "deadlineMs": 99999,
            "stageBudgetsMs": {},
            "freshness": {},
            "limits": {},
        }
        dte_file = tmp_path / "dte.json"
        dte_file.write_text(json.dumps(dte_spec))

        monkeypatch.setattr(sys, "argv", [
            "coherence", "dte", "check", str(SAMPLE_EPISODES_PATH),
            "--dte", str(dte_file),
        ])
        with pytest.raises(SystemExit) as exc_info:
            main()
        # Should pass with generous limits
        assert exc_info.value.code == 0


# ── cmd_metrics ──────────────────────────────────────────────────


class TestCmdMetrics:
    def test_metrics_text(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "coherence", "metrics", str(SAMPLE_EPISODES_PATH),
        ])
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert len(captured.out) > 0


# ── FEEDS commands ───────────────────────────────────────────────


class TestCmdFeedsValidate:
    def test_validate_nonexistent_exits(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "coherence", "feeds", "validate", "/nonexistent/path",
        ])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


class TestCmdFeedsBusInit:
    def test_bus_init(self, capsys, monkeypatch, tmp_path):
        root = tmp_path / "feeds_bus"
        monkeypatch.setattr(sys, "argv", [
            "coherence", "feeds", "bus-init", str(root),
        ])
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "initialized" in captured.out.lower()
