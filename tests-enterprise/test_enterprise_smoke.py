"""Enterprise smoke tests — verify core imports, key module instantiation,
and edition guard compliance from the enterprise context."""

import subprocess
import sys
from pathlib import Path


def test_enterprise_pyproject_exists() -> None:
    assert Path("enterprise/pyproject.toml").exists()


def test_core_imports_from_enterprise() -> None:
    from core import (
        DLRBuilder,
        DriftSignalCollector,
        MemoryGraph,
        ReflectionSession,
    )
    assert DLRBuilder is not None
    assert DriftSignalCollector is not None
    assert MemoryGraph is not None
    assert ReflectionSession is not None


def test_instantiate_dlr_builder() -> None:
    from core import DLRBuilder
    builder = DLRBuilder()
    assert hasattr(builder, "from_episode")
    assert hasattr(builder, "from_episodes")
    assert hasattr(builder, "entries")


def test_instantiate_memory_graph() -> None:
    from core import MemoryGraph
    mg = MemoryGraph()
    assert mg.node_count == 0
    assert mg.edge_count == 0


def test_instantiate_prime_gate() -> None:
    from core.prime import PRIMEGate, PRIMEConfig
    gate = PRIMEGate()
    assert gate.config is not None
    config = PRIMEConfig()
    assert config.validate() == []


def test_edition_guard_passes() -> None:
    result = subprocess.run(
        [sys.executable, "enterprise/scripts/edition_guard.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Edition guard failed: {result.stdout}\n{result.stderr}"
