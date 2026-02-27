#!/usr/bin/env python3
"""
Constitution Gate — enforces the immutable contract surface.

Checks:
  1. Schema fingerprints match manifest (detects silent breaks)
  2. Policy version parity (POLICY_VERSION.txt ↔ pyproject.toml)
  3. GPE sub-scan on constitution paths
  4. VERSION file reflects pyproject.toml

Usage:
  python scripts/constitution_gate.py          # validate
  python scripts/constitution_gate.py --init   # regenerate manifest after intentional changes
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "reference"
SCHEMAS_DIR = (REF / "schemas").resolve()
FEEDS_DIR = SCHEMAS_DIR / "feeds"
MANIFEST = REF / "schema_manifest.json"
VERSION_FILE = REF / "VERSION"
GATE_REPORT = REF / "GATE_REPORT.md"
PYPROJECT = ROOT / "pyproject.toml"
POLICY_VERSION = (REF / "governance" / "POLICY_VERSION.txt").resolve()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_schemas() -> dict[str, str]:
    """Collect all .schema.json files under schemas/ and schemas/feeds/."""
    schemas: dict[str, str] = {}
    for d in [SCHEMAS_DIR, FEEDS_DIR]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.schema.json")):
            key = f.relative_to(SCHEMAS_DIR).as_posix()
            schemas[key] = sha256_file(f)
    return schemas


def read_pyproject_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        return "UNKNOWN"
    return m.group(1)


def read_policy_version() -> str:
    if not POLICY_VERSION.exists():
        return "MISSING"
    raw = POLICY_VERSION.read_text(encoding="utf-8").strip()
    # Extract numeric part from "GOV-X.Y.Z"
    m = re.match(r"GOV-(.+)", raw)
    return m.group(1) if m else raw


def major_minor(v: str) -> str:
    parts = v.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else v


def run_gpe_subscan() -> tuple[bool, str]:
    """Run GPE on constitution-resolved paths."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/domain_scrub.py", "--paths", "reference"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=30,
        )
        passed = result.returncode == 0
        return passed, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def init_manifest(schemas: dict[str, str], version: str) -> None:
    """Generate fresh schema manifest."""
    manifest = {
        "version": version,
        "generated": datetime.now(timezone.utc).isoformat(),
        "schema_count": len(schemas),
        "schemas": schemas,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def validate_manifest(schemas: dict[str, str]) -> list[str]:
    """Compare current schemas against stored manifest."""
    if not MANIFEST.exists():
        return ["schema_manifest.json not found. Run with --init to generate."]

    stored = json.loads(MANIFEST.read_text(encoding="utf-8"))
    stored_schemas = stored.get("schemas", {})
    errors = []

    # Check for changed hashes
    for name, current_hash in schemas.items():
        stored_hash = stored_schemas.get(name)
        if stored_hash is None:
            errors.append(f"NEW schema not in manifest: {name}")
        elif stored_hash != current_hash:
            errors.append(f"CHANGED schema: {name} (hash mismatch)")

    # Check for removed schemas
    for name in stored_schemas:
        if name not in schemas:
            errors.append(f"REMOVED schema: {name} (still in manifest)")

    return errors


def write_version(version: str) -> None:
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")


def write_report(checks: list[tuple[str, bool, str]]) -> bool:
    lines = [
        "# Constitution Gate Report",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    all_pass = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        lines.append(f"## {name}: {status}")
        lines.append("")
        if detail:
            lines.append(detail)
            lines.append("")

    overall = "PASS" if all_pass else "FAIL"
    lines.insert(3, f"**Result:** {overall}")
    lines.insert(4, "")

    GATE_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return all_pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Constitution Gate")
    ap.add_argument("--init", action="store_true", help="Regenerate schema manifest")
    args = ap.parse_args()

    pyproject_v = read_pyproject_version()
    policy_v = read_policy_version()
    schemas = collect_schemas()
    checks: list[tuple[str, bool, str]] = []

    # 1. Schema fingerprints
    if args.init:
        init_manifest(schemas, pyproject_v)
        checks.append(("Schema Fingerprints", True,
                        f"Manifest regenerated. {len(schemas)} schemas locked."))
    else:
        errors = validate_manifest(schemas)
        if errors:
            detail = "Run `python scripts/constitution_gate.py --init` after adding CHANGELOG.md entry.\n\n"
            detail += "\n".join(f"- {e}" for e in errors)
            checks.append(("Schema Fingerprints", False, detail))
        else:
            checks.append(("Schema Fingerprints", True,
                            f"{len(schemas)} schemas match manifest."))

    # 2. Version parity
    py_mm = major_minor(pyproject_v)
    pol_mm = major_minor(policy_v)
    if pol_mm == py_mm:
        checks.append(("Version Parity", True,
                        f"pyproject={pyproject_v} policy=GOV-{policy_v}"))
    else:
        checks.append(("Version Parity", False,
                        f"pyproject={pyproject_v} (→{py_mm}) vs policy=GOV-{policy_v} (→{pol_mm})"))

    # 3. GPE sub-scan
    gpe_pass, gpe_output = run_gpe_subscan()
    # Extract summary line
    summary = [l for l in gpe_output.splitlines() if "PASS" in l or "FAIL" in l]
    checks.append(("GPE Sub-Scan", gpe_pass,
                    summary[-1].strip() if summary else gpe_output.strip()))

    # 4. VERSION file
    write_version(pyproject_v)
    checks.append(("VERSION File", True, f"Written: {pyproject_v}"))

    # Write report
    all_pass = write_report(checks)

    # Print summary
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {detail.splitlines()[0] if detail else ''}")

    if all_pass:
        print(f"\nConstitution Gate: PASS ({len(schemas)} schemas, version {pyproject_v})")
        return 0
    else:
        print("\nConstitution Gate: FAIL — see reference/GATE_REPORT.md")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
