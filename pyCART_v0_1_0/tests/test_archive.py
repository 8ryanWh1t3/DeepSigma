from dataclasses import replace
import sqlite3
import subprocess
import sys
import pytest
from deepsigma_cartography import ConflictError, EditionStore, IntegrityError, ValidationError
from deepsigma_cartography.sample import AS_OF


def test_archive_roundtrip_and_restart(atlas,tmp_path):
    p=tmp_path/'map.db'
    with EditionStore.create(p,atlas_id=atlas.id) as store:
        first=store.append(atlas,recorded_at=AS_OF,expected_parent=None)
        second=store.append(replace(atlas,title='Candidate'),recorded_at=AS_OF,expected_parent=first.edition_hash)
        assert store.get(1).atlas.fingerprint==atlas.fingerprint
        assert store.head==second.edition_hash
    with EditionStore.open(p,expected_head=second.edition_hash) as store:
        assert len(store.editions())==2
        assert store.get(1).edition_hash==first.edition_hash

def test_missing_archive_is_not_genesis(tmp_path):
    p=tmp_path/'missing.db'
    with pytest.raises(IntegrityError): EditionStore.open(p)
    assert not p.exists()

def test_create_never_overwrites(atlas,tmp_path):
    p=tmp_path/'archive.db'
    with EditionStore.create(p,atlas_id=atlas.id): pass
    before=p.read_bytes()
    with pytest.raises(FileExistsError): EditionStore.create(p,atlas_id=atlas.id)
    assert p.read_bytes()==before

def test_corrupt_database_rejected(tmp_path):
    p=tmp_path/'bad.db';p.write_bytes(b'not a sqlite database')
    with pytest.raises(IntegrityError): EditionStore.open(p)
    assert p.read_bytes()==b'not a sqlite database'

def test_cas_rejects_stale_writer(atlas,tmp_path):
    p=tmp_path/'archive.db'
    with EditionStore.create(p,atlas_id=atlas.id) as first, EditionStore.open(p) as second:
        old=second.head
        edition=first.append(atlas,recorded_at=AS_OF,expected_parent=None)
        with pytest.raises(ConflictError): second.append(atlas,recorded_at=AS_OF,expected_parent=old)
        assert first.head==edition.edition_hash

def test_failed_append_does_not_advance_head(atlas,tmp_path):
    with EditionStore.create(tmp_path/'a.db',atlas_id=atlas.id) as store:
        with pytest.raises(ValidationError): store.append(replace(atlas,id='other'),recorded_at=AS_OF,expected_parent=None)
        assert store.head is None
        assert not store.editions()

def test_backward_time_rejected(atlas,tmp_path):
    with EditionStore.create(tmp_path/'a.db',atlas_id=atlas.id) as store:
        first=store.append(atlas,recorded_at=AS_OF,expected_parent=None)
        with pytest.raises(ValidationError): store.append(atlas,recorded_at='2025-01-01T00:00:00Z',expected_parent=first.edition_hash)
        assert store.head==first.edition_hash

def test_record_tamper_rejected(atlas,tmp_path):
    p=tmp_path/'a.db'
    with EditionStore.create(p,atlas_id=atlas.id) as store:
        store.append(atlas,recorded_at=AS_OF,expected_parent=None)
    with sqlite3.connect(p) as db:
        db.execute("UPDATE editions SET body='{}' WHERE seq=1")
    with pytest.raises(IntegrityError): EditionStore.open(p)

def test_tail_deletion_rejected(atlas,tmp_path):
    p=tmp_path/'a.db'
    with EditionStore.create(p,atlas_id=atlas.id) as store:
        first=store.append(atlas,recorded_at=AS_OF,expected_parent=None)
        store.append(atlas,recorded_at=AS_OF,expected_parent=first.edition_hash)
    with sqlite3.connect(p) as db: db.execute('DELETE FROM editions WHERE seq=2')
    with pytest.raises(IntegrityError): EditionStore.open(p)

def test_pin_detects_whole_file_rollback(atlas,tmp_path):
    p=tmp_path/'a.db'
    with EditionStore.create(p,atlas_id=atlas.id) as store:
        first=store.append(atlas,recorded_at=AS_OF,expected_parent=None)
    old=p.read_bytes()
    with EditionStore.open(p) as store:
        second=store.append(atlas,recorded_at=AS_OF,expected_parent=first.edition_hash)
    p.write_bytes(old)
    # A local unsigned chain alone cannot detect restoration of the entire file.
    with EditionStore.open(p) as store: assert store.head==first.edition_hash
    with pytest.raises(IntegrityError): EditionStore.open(p,expected_head=second.edition_hash)

def test_real_subprocess_reopens_and_verifies(atlas,tmp_path):
    p=tmp_path/'a.db'
    with EditionStore.create(p,atlas_id=atlas.id) as store:
        first=store.append(atlas,recorded_at=AS_OF,expected_parent=None)
    script='from deepsigma_cartography import EditionStore; import sys; s=EditionStore.open(sys.argv[1],expected_head=sys.argv[2]); print(s.head); s.close()'
    proc=subprocess.run([sys.executable,'-c',script,str(p),first.edition_hash],capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    assert proc.stdout.strip()==first.edition_hash

def test_invalid_sequence(atlas,tmp_path):
    with EditionStore.create(tmp_path/'a.db',atlas_id=atlas.id) as store:
        for value in (0,-1,True,1):
            with pytest.raises(ValidationError): store.get(value)

def test_sqlite_write_failure_propagates(atlas,tmp_path):
    with EditionStore.create(tmp_path/'a.db',atlas_id=atlas.id) as store:
        store._db.execute('PRAGMA query_only=ON')
        with pytest.raises(sqlite3.OperationalError): store.append(atlas,recorded_at=AS_OF,expected_parent=None)
        store._db.execute('PRAGMA query_only=OFF')
        assert store.head is None
