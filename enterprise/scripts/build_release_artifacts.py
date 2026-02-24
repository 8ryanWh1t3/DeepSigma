#!/usr/bin/env python3
"""Build edition artifacts for DeepSigma from tracked files."""

from __future__ import annotations

import subprocess
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"

CORE_TOP = {
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "Makefile",
    "README.md",
    "SECURITY.md",
    "core_baseline.py",
    "pyproject.toml",
    "requirements.txt",
    "run_money_demo.sh",
}


def version() -> str:
    line = next(
        candidate
        for candidate in (ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines()
        if candidate.startswith("version = ")
    )
    return line.split("=", 1)[1].strip().strip('"')


def tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [p for p in out.splitlines() if p]


def is_core_file(path: str) -> bool:
    p = Path(path)
    if path in CORE_TOP:
        return True
    if p.parts[0] in {"docs", "tests", "requirements", "src"}:
        if p.parts[0] == "src":
            # Core edition ships only core namespace + temporary shim.
            return len(p.parts) > 1 and p.parts[1] in {"core", "coherence_ops"}
        return True
    return False


def build_zip(name: str, files: list[str]) -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / name
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(files):
            abs_path = ROOT / rel
            if abs_path.is_file():
                zf.write(abs_path, arcname=rel)
    return out


def main() -> int:
    v = version()
    files = tracked_files()

    core_files = [f for f in files if is_core_file(f)]
    enterprise_files = files

    core_name = f"deepsigma-core-v{v}.zip"
    ent_name = f"deepsigma-enterprise-v{v}.zip"

    core_zip = build_zip(core_name, core_files)
    ent_zip = build_zip(ent_name, enterprise_files)

    print(f"PASS: {core_zip.relative_to(ROOT)} ({len(core_files)} files)")
    print(f"PASS: {ent_zip.relative_to(ROOT)} ({len(enterprise_files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
