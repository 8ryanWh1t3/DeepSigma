"""Shared fixtures for langchain-deepsigma tests."""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

import pytest

# Ensure the package src is importable
PKG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG_ROOT / "src"))

# Also ensure core is importable from repo root
REPO_ROOT = PKG_ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


@pytest.fixture
def run_id():
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def parent_run_id():
    return UUID("abcdefab-cdef-abcd-efab-cdefabcdefab")


class MockDTEViolation:
    """Mimics a DTE violation object."""

    def __init__(self, gate="timeout", field="elapsed_ms", limit=100, actual=200):
        self.gate = gate
        self.field = field
        self.limit_value = limit
        self.actual_value = actual
        self.severity = "red"
        self.message = f"{gate}: {field} {actual} > {limit}"


class MockDTEEnforcer:
    """Mock DTE enforcer for testing governance callbacks."""

    def __init__(self, violations=None):
        self._violations = violations or []

    def enforce(self, elapsed_ms=0, counts=None):
        return self._violations


@pytest.fixture
def mock_enforcer_clean():
    return MockDTEEnforcer(violations=[])


@pytest.fixture
def mock_enforcer_violating():
    return MockDTEEnforcer(violations=[MockDTEViolation()])
