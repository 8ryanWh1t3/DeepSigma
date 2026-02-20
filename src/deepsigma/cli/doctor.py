"""deepsigma doctor — environment health check."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_TEMPLATE = (
    _REPO_ROOT / "templates" / "creative_director_suite"
    / "Creative_Director_Suite_CoherenceOps_v2.xlsx"
)


def _try_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


CHECKS: list[tuple[str, bool, object]] = [
    # (label, optional, check_fn)
    ("Python >= 3.10", False, lambda: sys.version_info >= (3, 10)),
    ("jsonschema importable", False, lambda: _try_import("jsonschema")),
    ("pyyaml importable", False, lambda: _try_import("yaml")),
    ("openpyxl importable", True, lambda: _try_import("openpyxl")),
    ("pyproject.toml exists", False, lambda: (_REPO_ROOT / "pyproject.toml").exists()),
    ("coherence_ops/ exists", False, lambda: (_REPO_ROOT / "coherence_ops").is_dir()),
    ("engine/ exists", False, lambda: (_REPO_ROOT / "engine").is_dir()),
    ("tools/ exists", False, lambda: (_REPO_ROOT / "tools").is_dir()),
    ("specs/ exists", False, lambda: (_REPO_ROOT / "specs").is_dir()),
    ("mdpt/ exists", False, lambda: (_REPO_ROOT / "mdpt").is_dir()),
    ("CDS template exists", False, lambda: _TEMPLATE.exists()),
    ("boot validator importable", False, lambda: _try_import("tools.validate_workbook_boot")),
]


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("doctor", help="Environment health check")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    import json as json_mod

    results = []
    all_pass = True
    for label, optional, check_fn in CHECKS:
        ok = check_fn()
        results.append({"check": label, "ok": ok, "optional": optional})
        if not ok and not optional:
            all_pass = False

    if getattr(args, "json", False):
        print(json_mod.dumps({"passed": all_pass, "checks": results}, indent=2))
    else:
        print()
        print("deepsigma doctor")
        print("=" * 50)
        for r in results:
            if r["ok"]:
                tag = "PASS"
            elif r["optional"]:
                tag = "WARN"
            else:
                tag = "FAIL"
            print(f"  [{tag}] {r['check']}")
        print("=" * 50)
        print(f"  Result: {'HEALTHY' if all_pass else 'ISSUES DETECTED'}")
        print()

    return 0 if all_pass else 1
