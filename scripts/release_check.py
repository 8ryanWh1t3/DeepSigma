#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"\s*$')
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")


def detect_tag(explicit_tag: str | None) -> str:
    if explicit_tag:
        return explicit_tag.strip()

    env_tag = os.environ.get("GITHUB_REF_NAME")
    if env_tag:
        return env_tag.strip()

    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        raise SystemExit(
            "Unable to detect release tag. Provide --tag vX.Y.Z or run on a tag ref."
        )


def read_pyproject_version() -> str:
    for line in PYPROJECT.read_text(encoding="utf-8").splitlines():
        match = VERSION_RE.match(line.strip())
        if match:
            return match.group(1)
    raise SystemExit(f"Could not find project version in {PYPROJECT}.")


def changelog_has_version(version: str) -> bool:
    needle = f"## [{version}]"
    return needle in CHANGELOG.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tag/version/changelog for release")
    parser.add_argument("--tag", help="Tag to validate (e.g. v2.0.3)")
    args = parser.parse_args()

    tag = detect_tag(args.tag)
    match = TAG_RE.match(tag)
    if not match:
        print(f"ERROR: Tag '{tag}' must match vX.Y.Z", file=sys.stderr)
        return 1

    tag_version = match.group(1)
    project_version = read_pyproject_version()

    failed = False
    if project_version != tag_version:
        print(
            "ERROR: pyproject version mismatch: "
            f"pyproject={project_version} tag={tag_version}",
            file=sys.stderr,
        )
        failed = True

    if not changelog_has_version(tag_version):
        print(
            f"ERROR: Missing changelog heading '## [{tag_version}]' in {CHANGELOG}",
            file=sys.stderr,
        )
        failed = True

    if failed:
        return 1

    print("Release check passed")
    print(f"- tag: {tag}")
    print(f"- version: {project_version}")
    print(f"- changelog: {CHANGELOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
