"""Tests for MDPT Power App deployment package.

Validates package generation, schema integrity,
and flow template structure.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO = Path(__file__).resolve().parents[1]


class TestPackageBuilder:
    """Verify .zip package generation."""

    def test_package_creates_zip(self, tmp_path):
        from mdpt.tools.package_power_app import (
            build_package,
        )

        zp = build_package(tmp_path)
        assert zp.exists()
        assert zp.suffix == ".zip"

    def test_package_contains_required_files(
        self, tmp_path,
    ):
        from mdpt.tools.package_power_app import (
            build_package,
        )

        zp = build_package(tmp_path)
        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()

        required = [
            "docs/power_app_deployment.md",
            "powerapps/STARTER_KIT.md",
            "powerapps/POWERAPPS_SCREEN_MAP.md",
            "powerapps/sharepoint_list_schema.json",
            "powerapps/flow_scheduled_index_regen.json",
            "tools/generate_prompt_index.py",
            "templates/prompt_index_schema.json",
            "MANIFEST.txt",
        ]
        for f in required:
            assert f in names, f"Missing: {f}"

    def test_package_has_6_powerfx(self, tmp_path):
        from mdpt.tools.package_power_app import (
            build_package,
        )

        zp = build_package(tmp_path)
        with zipfile.ZipFile(zp) as zf:
            pfx = [
                n for n in zf.namelist()
                if n.endswith(".pfx")
            ]
        assert len(pfx) == 6

    def test_manifest_text(self, tmp_path):
        from mdpt.tools.package_power_app import (
            build_package,
        )

        zp = build_package(tmp_path)
        with zipfile.ZipFile(zp) as zf:
            manifest = zf.read(
                "MANIFEST.txt",
            ).decode()
        assert "MDPT Power App" in manifest
        assert "power_app_deployment.md" in manifest


class TestSharePointListSchema:
    """Validate SharePoint list schema JSON."""

    def test_schema_loads(self):
        path = (
            REPO / "mdpt" / "powerapps"
            / "sharepoint_list_schema.json"
        )
        data = json.loads(
            path.read_text(encoding="utf-8"),
        )
        assert "lists" in data

    def test_three_lists(self):
        path = (
            REPO / "mdpt" / "powerapps"
            / "sharepoint_list_schema.json"
        )
        data = json.loads(
            path.read_text(encoding="utf-8"),
        )
        lists = data["lists"]
        assert len(lists) == 3
        names = {lst["name"] for lst in lists}
        assert names == {
            "PromptCapabilities",
            "PromptRuns",
            "DriftPatches",
        }

    def test_capabilities_has_columns(self):
        path = (
            REPO / "mdpt" / "powerapps"
            / "sharepoint_list_schema.json"
        )
        data = json.loads(
            path.read_text(encoding="utf-8"),
        )
        caps = next(
            lst for lst in data["lists"]
            if lst["name"] == "PromptCapabilities"
        )
        col_names = [
            c["name"] for c in caps["columns"]
        ]
        assert "Capability_ID" in col_names
        assert "Lens" in col_names
        assert "Risk_Lane" in col_names
        assert "Status" in col_names

    def test_drift_patches_has_severity(self):
        path = (
            REPO / "mdpt" / "powerapps"
            / "sharepoint_list_schema.json"
        )
        data = json.loads(
            path.read_text(encoding="utf-8"),
        )
        drift = next(
            lst for lst in data["lists"]
            if lst["name"] == "DriftPatches"
        )
        sev = next(
            c for c in drift["columns"]
            if c["name"] == "Severity"
        )
        assert "CRITICAL" in sev["choices"]
        assert "HIGH" in sev["choices"]


class TestFlowTemplate:
    """Validate Power Automate flow template."""

    def test_flow_loads(self):
        path = (
            REPO / "mdpt" / "powerapps"
            / "flow_scheduled_index_regen.json"
        )
        data = json.loads(
            path.read_text(encoding="utf-8"),
        )
        assert "triggers" in data
        assert "actions" in data

    def test_flow_has_recurrence_trigger(self):
        path = (
            REPO / "mdpt" / "powerapps"
            / "flow_scheduled_index_regen.json"
        )
        data = json.loads(
            path.read_text(encoding="utf-8"),
        )
        trigger = data["triggers"]["Recurrence"]
        assert trigger["type"] == "Recurrence"
        sched = trigger["recurrence"]["schedule"]
        assert "Monday" in sched["weekDays"]

    def test_flow_has_teams_action(self):
        path = (
            REPO / "mdpt" / "powerapps"
            / "flow_scheduled_index_regen.json"
        )
        data = json.loads(
            path.read_text(encoding="utf-8"),
        )
        assert "Post_Teams_Summary" in data["actions"]

    def test_flow_metadata(self):
        path = (
            REPO / "mdpt" / "powerapps"
            / "flow_scheduled_index_regen.json"
        )
        data = json.loads(
            path.read_text(encoding="utf-8"),
        )
        meta = data["metadata"]
        assert "MDPT" in meta["name"]
        assert meta["version"] == "1.0"
