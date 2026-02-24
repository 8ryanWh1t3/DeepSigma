from pathlib import Path


def test_enterprise_surface_present() -> None:
    assert Path("enterprise").exists()
