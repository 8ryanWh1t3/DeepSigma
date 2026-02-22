"""Regression tests for stateless credibility API runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from credibility_engine import api as credibility_api
from credibility_engine.constants import DEFAULT_TENANT_ID
from credibility_engine.store import CredibilityStore


def _temp_store_factory(base: Path):
    def _factory(tenant_id: str) -> CredibilityStore:
        return CredibilityStore(
            data_dir=base / tenant_id,
            tenant_id=tenant_id,
        )

    return _factory


@pytest.fixture(autouse=True)
def _restore_store_factory():
    previous = credibility_api._store_factory
    yield
    credibility_api.set_store_factory(previous)


def test_get_engine_is_request_scoped(tmp_path):
    credibility_api.set_store_factory(_temp_store_factory(tmp_path))

    engine_a = credibility_api._get_engine("tenant-alpha")
    engine_b = credibility_api._get_engine("tenant-alpha")

    assert engine_a is not engine_b


def test_state_persists_across_fresh_engine_instances(tmp_path):
    credibility_api.set_store_factory(_temp_store_factory(tmp_path))

    first = credibility_api._get_engine("tenant-alpha")
    updated = first.update_claim_state("CLM-T0-001", state="DEGRADED")
    assert updated is not None

    second = credibility_api._get_engine("tenant-alpha")
    claim = next(c for c in second.claims if c.id == "CLM-T0-001")

    assert claim.state == "DEGRADED"


def test_reset_engine_writes_through_persistence_layer(tmp_path):
    credibility_api.set_store_factory(_temp_store_factory(tmp_path))

    engine = credibility_api.reset_engine(tenant_id=DEFAULT_TENANT_ID)
    engine.update_claim_state("CLM-T0-001", state="DEGRADED")

    reloaded = credibility_api._get_engine(DEFAULT_TENANT_ID)
    claim = next(c for c in reloaded.claims if c.id == "CLM-T0-001")

    assert claim.state == "DEGRADED"
