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
KPI_VERSION = ROOT / "release_kpis" / "VERSION.txt"
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


def read_kpi_version() -> str:
    raw = KPI_VERSION.read_text(encoding="utf-8").strip()
    return raw[1:] if raw.startswith("v") else raw


def verify_tag_is_main_head() -> tuple[bool, str]:
    """Ensure the tagged commit is exactly the current origin/main HEAD."""
    try:
        subprocess.check_call(
            ["git", "fetch", "origin", "main"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        tag_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
        main_commit = subprocess.check_output(
            ["git", "rev-parse", "origin/main"],
            cwd=ROOT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError as exc:
        return False, f"Unable to resolve commit refs for strict main-head check: {exc}"

    if tag_commit != main_commit:
        return (
            False,
            "Tag commit is not origin/main HEAD: "
            f"tag_commit={tag_commit} origin/main={main_commit}",
        )

    return True, main_commit


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tag/version/changelog for release")
    parser.add_argument("--tag", help="Tag to validate (e.g. v2.0.3)")
    parser.add_argument(
        "--require-main-head",
        action="store_true",
        help="Require the tag to point to the current origin/main HEAD.",
    )
    args = parser.parse_args()

    tag = detect_tag(args.tag)
    match = TAG_RE.match(tag)
    if not match:
        print(f"ERROR: Tag '{tag}' must match vX.Y.Z", file=sys.stderr)
        return 1

    tag_version = match.group(1)
    project_version = read_pyproject_version()
    kpi_version = read_kpi_version()

    failed = False
    if project_version != tag_version:
        print(
            "ERROR: pyproject version mismatch: "
            f"pyproject={project_version} tag={tag_version}",
            file=sys.stderr,
        )
        failed = True

    if kpi_version != tag_version:
        print(
            "ERROR: release_kpis/VERSION.txt mismatch: "
            f"kpi={kpi_version} tag={tag_version}",
            file=sys.stderr,
        )
        failed = True

    if not changelog_has_version(tag_version):
        print(
            f"ERROR: Missing changelog heading '## [{tag_version}]' in {CHANGELOG}",
            file=sys.stderr,
        )
        failed = True

    strict_main_head = args.require_main_head or os.environ.get(
        "RELEASE_CHECK_REQUIRE_MAIN_HEAD"
    ) == "1"
    strict_main_head_ref = ""
    if strict_main_head:
        ok, result = verify_tag_is_main_head()
        if not ok:
            print(f"ERROR: {result}", file=sys.stderr)
            failed = True
        else:
            strict_main_head_ref = result

    if failed:
        return 1

    print("Release check passed")
    print(f"- tag: {tag}")
    print(f"- version: {project_version}")
    print(f"- kpi version: {kpi_version}")
    print(f"- changelog: {CHANGELOG}")
    if strict_main_head:
        print(f"- origin/main HEAD: {strict_main_head_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
