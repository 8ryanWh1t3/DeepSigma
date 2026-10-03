import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import pytest
from vinculum_folding import EpisodeJournal, FoldEpisode, FoldError


def later(episode):
    return episode.revise(recorded_at="2026-10-03T11:00:00-04:00", title="Second revision")


def test_append_and_read_only(episode, tmp_path):
    path = tmp_path / "episodes.db"
    with EpisodeJournal.create(path) as j:
        assert j.append(episode) == episode.digest
        j.append(later(episode))
        assert j.get(episode.episode_id, 1) == episode
        assert len(j.history(episode.episode_id)) == 2
    with EpisodeJournal.open(path) as j:
        assert j.get(episode.episode_id).revision == 2
        assert j.verify(episode.episode_id, expected_tip=later(episode).digest)["expected_tip_checked"]
        with pytest.raises(FoldError): j.append(later(episode))


def test_actual_process_restart(episode, tmp_path):
    path = tmp_path / "episodes.db"
    with EpisodeJournal.create(path) as j:
        j.append(episode); j.append(later(episode))
    env = dict(os.environ)
    import vinculum_folding
    env["PYTHONPATH"] = str(Path(vinculum_folding.__file__).resolve().parents[1])
    command = ("from vinculum_folding import EpisodeJournal; "
               f"j=EpisodeJournal.open({str(path)!r}); "
               f"v=j.verify({episode.episode_id!r},expected_tip={later(episode).digest!r}); "
               "assert v['revisions']==2; print(v['tip_digest'])")
    result = subprocess.run([sys.executable, "-c", command], env=env, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == later(episode).digest


def test_duplicate_revision_rejected_without_changing_tip(episode, tmp_path):
    with EpisodeJournal.create(tmp_path / "e.db") as j:
        j.append(episode)
        with pytest.raises(FoldError): j.append(episode)
        assert j.get(episode.episode_id) == episode


def test_wrong_predecessor_rejected(episode, tmp_path):
    data = later(episode).to_dict(); data["previous_digest"] = "0" * 64
    with EpisodeJournal.create(tmp_path / "e.db") as j:
        j.append(episode)
        with pytest.raises(FoldError): j.append(FoldEpisode(data))
        assert len(j.history(episode.episode_id)) == 1


def test_missing_database_not_recreated(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(FoldError): EpisodeJournal.open(path, read_only=False)
    assert not path.exists()


def test_create_cannot_reset_existing_database(tmp_path):
    path = tmp_path / "e.db"
    with EpisodeJournal.create(path): pass
    old = path.read_bytes()
    with pytest.raises(FileExistsError): EpisodeJournal.create(path)
    assert path.read_bytes() == old


def test_corrupt_database_fails_closed(tmp_path):
    path = tmp_path / "bad.db"; path.write_bytes(b"not sqlite")
    with pytest.raises(FoldError): EpisodeJournal.open(path)
    assert path.read_bytes() == b"not sqlite"


def test_corrupt_snapshot_detected(episode, tmp_path):
    path = tmp_path / "e.db"
    with EpisodeJournal.create(path) as j: j.append(episode)
    with sqlite3.connect(path) as c:
        c.execute("UPDATE episodes SET payload='{}'")
    with EpisodeJournal.open(path) as j:
        with pytest.raises(FoldError): j.get(episode.episode_id)


def test_revision_gap_detected(episode, tmp_path):
    path = tmp_path / "e.db"
    with EpisodeJournal.create(path) as j: j.append(episode); j.append(later(episode))
    with sqlite3.connect(path) as c:
        c.execute("DELETE FROM episodes WHERE revision=1")
    with EpisodeJournal.open(path) as j:
        with pytest.raises(FoldError): j.verify(episode.episode_id)


def test_rollback_only_detectable_against_external_tip(episode, tmp_path):
    path, old = tmp_path / "e.db", tmp_path / "old.db"
    with EpisodeJournal.create(path) as j: j.append(episode)
    shutil.copyfile(path, old)
    with EpisodeJournal.open(path, read_only=False) as j: j.append(later(episode))
    shutil.copyfile(old, path)
    with EpisodeJournal.open(path) as j:
        assert j.verify(episode.episode_id)["revisions"] == 1  # internal consistency alone cannot detect this
        with pytest.raises(FoldError): j.verify(episode.episode_id, expected_tip=later(episode).digest)


def test_record_time_separate_from_event_time(episode, tmp_path):
    data = episode.to_dict()
    data["nodes"][0]["value"]["start"] = "2020-01-01T10:00:00Z"
    old_event = episode.revise(recorded_at="2026-10-03T11:00:00-04:00", nodes=data["nodes"])
    with EpisodeJournal.create(tmp_path / "e.db") as j:
        j.append(episode); j.append(old_event)
        assert j.get(episode.episode_id) == old_event


def test_backward_record_time_rejected(episode, tmp_path):
    early = episode.revise(recorded_at="2026-10-02T11:00:00-04:00")
    with EpisodeJournal.create(tmp_path / "e.db") as j:
        j.append(episode)
        with pytest.raises(FoldError): j.append(early)


def test_concurrent_stale_writer(episode, tmp_path):
    path = tmp_path / "e.db"
    with EpisodeJournal.create(path) as j: j.append(episode)
    with EpisodeJournal.open(path, read_only=False) as a, EpisodeJournal.open(path, read_only=False) as b:
        a.append(later(episode))
        with pytest.raises(FoldError): b.append(later(episode))
        assert len(b.history(episode.episode_id)) == 2


def test_absent_history_never_reports_verified(tmp_path):
    with EpisodeJournal.create(tmp_path / "e.db") as j:
        with pytest.raises(FoldError): j.verify("missing")
        with pytest.raises(FoldError): j.get("missing")
