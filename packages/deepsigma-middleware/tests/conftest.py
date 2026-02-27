"""Shared fixtures for deepsigma-middleware tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the package src is importable
PKG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG_ROOT / "src"))

# Also ensure core is importable from repo root
REPO_ROOT = PKG_ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
