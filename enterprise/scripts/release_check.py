#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
KPI_VERSION = ROOT / "release_kpis" / "VERSION.txt"
CHART_YAML = ROOT / "charts" / "deepsigma" / "Chart.yaml"
OPS_RUNBOOK = ROOT / "docs" / "OPS_RUNBOOK.md"
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


def check_chart_version() -> str | None:
    """Verify Chart.yaml appVersion is not a placeholder."""
    if not CHART_YAML.exists():
        return "Chart.yaml not found"
    content = CHART_YAML.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.strip().startswith("appVersion:"):
            version = line.split(":", 1)[1].strip().strip('"').strip("'")
            if version in ("0.0.0", "latest", ""):
                return f"Chart.yaml appVersion is placeholder: {version}"
            return None
    return "Chart.yaml missing appVersion field"


def check_runbook_sections() -> str | None:
    """Verify OPS_RUNBOOK.md contains the enterprise release checklist."""
    if not OPS_RUNBOOK.exists():
        return "OPS_RUNBOOK.md not found"
    content = OPS_RUNBOOK.read_text(encoding="utf-8")
    if "Enterprise Release Checklist" not in content:
        return "OPS_RUNBOOK.md missing Enterprise Release Checklist section"
    return None


def run_self_check() -> int:
    """Validate release_check internals with synthetic fixtures."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        charts = root / "charts" / "deepsigma"
        docs = root / "docs"
        charts.mkdir(parents=True)
        docs.mkdir(parents=True)

        # Test 1: missing chart should be detected
        global CHART_YAML, OPS_RUNBOOK
        orig_chart, orig_runbook = CHART_YAML, OPS_RUNBOOK
        CHART_YAML = charts / "Chart.yaml"
        OPS_RUNBOOK = docs / "OPS_RUNBOOK.md"

        err = check_chart_version()
        if err is None:
            CHART_YAML, OPS_RUNBOOK = orig_chart, orig_runbook
            print("FAIL: should detect missing Chart.yaml")
            return 2

        # Test 2: placeholder version should fail
        CHART_YAML.write_text('apiVersion: v2\nappVersion: "0.0.0"\n', encoding="utf-8")
        err = check_chart_version()
        if err is None:
            CHART_YAML, OPS_RUNBOOK = orig_chart, orig_runbook
            print("FAIL: placeholder appVersion should fail")
            return 2

        # Test 3: real version should pass
        CHART_YAML.write_text('apiVersion: v2\nappVersion: "2.0.11"\n', encoding="utf-8")
        err = check_chart_version()
        if err is not None:
            CHART_YAML, OPS_RUNBOOK = orig_chart, orig_runbook
            print(f"FAIL: valid appVersion should pass: {err}")
            return 2

        # Test 4: missing runbook should fail
        err = check_runbook_sections()
        if err is None:
            CHART_YAML, OPS_RUNBOOK = orig_chart, orig_runbook
            print("FAIL: should detect missing runbook")
            return 2

        # Test 5: runbook without checklist should fail
        OPS_RUNBOOK.write_text("# Runbook\n", encoding="utf-8")
        err = check_runbook_sections()
        if err is None:
            CHART_YAML, OPS_RUNBOOK = orig_chart, orig_runbook
            print("FAIL: runbook without checklist should fail")
            return 2

        # Test 6: runbook with checklist should pass
        OPS_RUNBOOK.write_text("# Runbook\n## 7. Enterprise Release Checklist\n", encoding="utf-8")
        err = check_runbook_sections()
        if err is not None:
            CHART_YAML, OPS_RUNBOOK = orig_chart, orig_runbook
            print(f"FAIL: valid runbook should pass: {err}")
            return 2

        CHART_YAML, OPS_RUNBOOK = orig_chart, orig_runbook

    print("PASS: release-check self-check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tag/version/changelog for release")
    parser.add_argument("--tag", help="Tag to validate (e.g. v2.0.3)")
    parser.add_argument(
        "--require-main-head",
        action="store_true",
        help="Require the tag to point to the current origin/main HEAD.",
    )
    parser.add_argument("--self-check", action="store_true", help="Run internal self-check")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

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

    chart_err = check_chart_version()
    if chart_err:
        print(f"ERROR: {chart_err}", file=sys.stderr)
        failed = True

    runbook_err = check_runbook_sections()
    if runbook_err:
        print(f"ERROR: {runbook_err}", file=sys.stderr)
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
    print(f"- chart: appVersion OK")
    print(f"- runbook: Enterprise Release Checklist present")
    if strict_main_head:
        print(f"- origin/main HEAD: {strict_main_head_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
