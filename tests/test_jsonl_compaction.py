"""Tests for JSONL evidence compaction."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from deepsigma.cli.compact import (
    compact_directory,
    compact_file,
    _dedupe_records,
    _load_jsonl,
    _strip_heartbeats,
    _tier_records,
    _write_jsonl,
)


NOW = datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc)


def _ts(days_ago: int) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


def _write_fixture(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestLoadWriteJSONL:
    def test_load_empty_file(self, tmp_path):
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        assert _load_jsonl(p) == []

    def test_load_missing_file(self, tmp_path):
        assert _load_jsonl(tmp_path / "nope.jsonl") == []

    def test_load_valid_records(self, tmp_path):
        p = tmp_path / "data.jsonl"
        _write_fixture(p, [{"id": "1"}, {"id": "2"}])
        records = _load_jsonl(p)
        assert len(records) == 2

    def test_load_skips_malformed(self, tmp_path):
        p = tmp_path / "data.jsonl"
        p.write_text('{"id": "1"}\nnot json\n{"id": "2"}\n')
        records = _load_jsonl(p)
        assert len(records) == 2

    def test_write_atomic(self, tmp_path):
        p = tmp_path / "out.jsonl"
        _write_jsonl(p, [{"a": 1}, {"b": 2}])
        records = _load_jsonl(p)
        assert len(records) == 2
        assert records[0]["a"] == 1


class TestDeduplication:
    def test_dedupe_by_id(self):
        records = [
            {"id": "a", "v": 1},
            {"id": "b", "v": 2},
            {"id": "a", "v": 3},  # duplicate, should win
        ]
        result = _dedupe_records(records, "id")
        by_id = {r["id"]: r for r in result}
        assert len(by_id) == 2
        assert by_id["a"]["v"] == 3

    def test_dedupe_preserves_no_id(self):
        records = [
            {"id": "a", "v": 1},
            {"v": 99},  # no id field
        ]
        result = _dedupe_records(records, "id")
        assert len(result) == 2


class TestHeartbeatStripping:
    def test_strips_heartbeats(self):
        records = [
            {"event_type": "heartbeat", "timestamp": "2026-02-19T10:00:00Z"},
            {"event_type": "heartbeat", "timestamp": "2026-02-19T10:15:00Z"},
            {"event_type": "heartbeat", "timestamp": "2026-02-19T10:30:00Z"},
            {"event_type": "prompt", "timestamp": "2026-02-19T10:05:00Z"},
        ]
        result = _strip_heartbeats(records)
        types = [r["event_type"] for r in result]
        assert types.count("prompt") == 1
        assert types.count("heartbeat") == 1  # one per hour

    def test_keeps_non_heartbeat(self):
        records = [
            {"event_type": "prompt", "timestamp": "2026-02-19T10:00:00Z"},
            {"event_type": "tool", "timestamp": "2026-02-19T10:01:00Z"},
        ]
        result = _strip_heartbeats(records)
        assert len(result) == 2


class TestTiering:
    def test_hot_warm_cold_split(self):
        records = [
            {"id": "hot", "timestamp": _ts(5)},     # 5 days ago → hot
            {"id": "warm", "timestamp": _ts(32)},    # 32 days ago → warm
            {"id": "cold", "timestamp": _ts(45)},    # 45 days ago → cold
        ]
        tiers = _tier_records(records, NOW, retention_days=30, warm_days=7)
        assert len(tiers["hot"]) == 1
        assert len(tiers["warm"]) == 1
        assert len(tiers["cold"]) == 1

    def test_all_hot(self):
        records = [
            {"id": "a", "timestamp": _ts(1)},
            {"id": "b", "timestamp": _ts(2)},
        ]
        tiers = _tier_records(records, NOW, retention_days=30, warm_days=7)
        assert len(tiers["hot"]) == 2
        assert len(tiers["warm"]) == 0
        assert len(tiers["cold"]) == 0

    def test_empty_records(self):
        tiers = _tier_records([], NOW, retention_days=30, warm_days=7)
        assert tiers == {"hot": [], "warm": [], "cold": []}


class TestCompactFile:
    def test_compact_creates_tiers(self, tmp_path):
        records = [
            {"id": "hot1", "timestamp": _ts(5)},
            {"id": "hot2", "timestamp": _ts(10)},
            {"id": "warm1", "timestamp": _ts(32)},
            {"id": "cold1", "timestamp": _ts(50)},
        ]
        path = tmp_path / "events.jsonl"
        _write_fixture(path, records)

        result = compact_file(path, retention_days=30, warm_days=7, now=NOW)
        assert result["original"] == 4
        assert result["hot"] == 2
        assert result["warm"] == 1
        assert result["cold"] == 1

        # Check files written
        assert path.exists()  # hot replaces original
        assert (tmp_path / "events-warm.jsonl").exists()
        assert (tmp_path / "events-cold.jsonl").exists()

        hot_records = _load_jsonl(path)
        assert len(hot_records) == 2

    def test_compact_dry_run(self, tmp_path):
        records = [
            {"id": "a", "timestamp": _ts(5)},
            {"id": "b", "timestamp": _ts(50)},
        ]
        path = tmp_path / "drift.jsonl"
        _write_fixture(path, records)

        result = compact_file(path, dry_run=True, now=NOW)
        assert result["hot"] == 1
        assert result["cold"] == 1

        # Original unchanged
        assert len(_load_jsonl(path)) == 2
        assert not (tmp_path / "drift-warm.jsonl").exists()

    def test_compact_deduplicates(self, tmp_path):
        records = [
            {"event_id": "a", "v": 1, "timestamp": _ts(1)},
            {"event_id": "a", "v": 2, "timestamp": _ts(1)},
            {"event_id": "b", "v": 3, "timestamp": _ts(1)},
        ]
        path = tmp_path / "events.jsonl"
        _write_fixture(path, records)

        result = compact_file(path, now=NOW)
        assert result["original"] == 3
        assert result["deduped"] == 2

    def test_compact_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        result = compact_file(path, now=NOW)
        assert result["original"] == 0

    def test_compact_strips_heartbeats(self, tmp_path):
        records = [
            {"event_id": "hb1", "event_type": "heartbeat", "timestamp": _ts(1)},
            {"event_id": "hb2", "event_type": "heartbeat", "timestamp": _ts(1)},
            {"event_id": "hb3", "event_type": "heartbeat", "timestamp": _ts(1)},
            {"event_id": "e1", "event_type": "prompt", "timestamp": _ts(1)},
        ]
        path = tmp_path / "events.jsonl"
        _write_fixture(path, records)

        result = compact_file(path, now=NOW)
        assert result["removed_heartbeats"] > 0


class TestCompactDirectory:
    def test_recursive_compaction(self, tmp_path):
        # Create nested structure
        _write_fixture(tmp_path / "events.jsonl", [
            {"event_id": "e1", "timestamp": _ts(1)},
        ])
        _write_fixture(tmp_path / "tenant-a" / "drift.jsonl", [
            {"drift_id": "d1", "timestamp": _ts(1)},
            {"drift_id": "d2", "timestamp": _ts(50)},
        ])

        results = compact_directory(tmp_path, retention_days=30, warm_days=7)
        assert len(results) == 2
        total_original = sum(r["original"] for r in results)
        assert total_original == 3

    def test_skips_warm_cold_files(self, tmp_path):
        _write_fixture(tmp_path / "events.jsonl", [
            {"event_id": "e1", "timestamp": _ts(1)},
        ])
        _write_fixture(tmp_path / "events-warm.jsonl", [
            {"event_id": "w1", "timestamp": _ts(35)},
        ])
        _write_fixture(tmp_path / "events-cold.jsonl", [
            {"event_id": "c1", "timestamp": _ts(60)},
        ])

        results = compact_directory(tmp_path)
        assert len(results) == 1  # only events.jsonl


class TestCLIIntegration:
    def test_compact_cli_runs(self, tmp_path):
        _write_fixture(tmp_path / "events.jsonl", [
            {"event_id": "e1", "timestamp": _ts(1)},
            {"event_id": "e2", "timestamp": _ts(50)},
        ])

        from deepsigma.cli.main import main
        rc = main(["compact", "--input", str(tmp_path), "--json"])
        assert rc == 0

    def test_compact_cli_dry_run(self, tmp_path):
        _write_fixture(tmp_path / "drift.jsonl", [
            {"drift_id": "d1", "timestamp": _ts(1)},
        ])

        from deepsigma.cli.main import main
        rc = main(["compact", "--input", str(tmp_path), "--dry-run"])
        assert rc == 0

    def test_compact_cli_bad_dir(self):
        from deepsigma.cli.main import main
        rc = main(["compact", "--input", "/nonexistent/path"])
        assert rc == 1
