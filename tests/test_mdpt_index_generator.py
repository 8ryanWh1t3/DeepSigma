"""Tests for mdpt/tools/generate_prompt_index.py — MDPT Prompt Index Generator."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES = REPO_ROOT / "tests" / "fixtures"
CSV_FIXTURE = FIXTURES / "promptcapabilities_export.csv"
SCHEMA_PATH = REPO_ROOT / "src" / "mdpt" / "templates" / "prompt_index_schema.json"


class TestCSVLoading:
    def test_loads_all_rows(self):
        from mdpt.tools.generate_prompt_index import load_csv

        rows = load_csv(str(CSV_FIXTURE))
        assert len(rows) == 8

    def test_filters_approved_only(self):
        from mdpt.tools.generate_prompt_index import filter_approved, load_csv

        rows = load_csv(str(CSV_FIXTURE))
        approved = filter_approved(rows)
        assert len(approved) == 6
        assert all(r["Status"].strip().lower() == "approved" for r in approved)

    def test_include_nonapproved(self):
        from mdpt.tools.generate_prompt_index import filter_approved, load_csv

        rows = load_csv(str(CSV_FIXTURE))
        all_rows = filter_approved(rows, include_nonapproved=True)
        assert len(all_rows) == 8


class TestValidation:
    def test_valid_rows_pass(self):
        from mdpt.tools.generate_prompt_index import (
            filter_approved,
            load_csv,
            validate_required,
        )

        rows = filter_approved(load_csv(str(CSV_FIXTURE)))
        for i, row in enumerate(rows, 1):
            errors = validate_required(row, i)
            assert errors == [], f"Row {i} had errors: {errors}"

    def test_missing_field_detected(self):
        from mdpt.tools.generate_prompt_index import validate_required

        row = {"CapabilityID": "CAP-TEST", "Title": "Test"}
        errors = validate_required(row, 1)
        assert len(errors) >= 8  # most required fields missing

    def test_invalid_risk_lane_detected(self):
        from mdpt.tools.generate_prompt_index import validate_required

        row = {f: "x" for f in [
            "CapabilityID", "Title", "Status", "RiskLane", "TTL_Hours",
            "LatestVersion", "LatestApprovedDate", "LatestPromptMatrixLink",
            "ExamplesLink", "ManifestLink",
        ]}
        row["RiskLane"] = "INVALID"
        errors = validate_required(row, 1)
        assert any("invalid RiskLane" in e for e in errors)


class TestNormalization:
    def test_numeric_fields_coerced(self):
        from mdpt.tools.generate_prompt_index import normalize_row

        row = {
            "CapabilityID": "CAP-TEST", "Title": "Test", "Status": "Approved",
            "RiskLane": "green", "TTL_Hours": "48", "LatestVersion": "1.0.0",
            "LatestApprovedDate": "2026-02-10", "LatestPromptMatrixLink": "https://x",
            "ExamplesLink": "https://e", "ManifestLink": "https://m",
            "RunCount": "12", "DriftCount": "", "LastEvalScore": "4.5",
        }
        out = normalize_row(row)
        assert out["ttl_hours"] == 48.0
        assert out["telemetry"]["run_count"] == 12
        assert out["telemetry"]["drift_count"] is None
        assert out["telemetry"]["last_eval_score"] == 4.5

    def test_risk_lane_uppercased(self):
        from mdpt.tools.generate_prompt_index import normalize_row

        row = {
            "CapabilityID": "CAP-TEST", "Title": "T", "Status": "Approved",
            "RiskLane": "yellow", "TTL_Hours": "24", "LatestVersion": "1.0",
            "LatestApprovedDate": "", "LatestPromptMatrixLink": "x",
            "ExamplesLink": "e", "ManifestLink": "m",
        }
        out = normalize_row(row)
        assert out["risk_lane"] == "YELLOW"

    def test_tags_split(self):
        from mdpt.tools.generate_prompt_index import normalize_row

        row = {
            "CapabilityID": "CAP-TEST", "Title": "T", "Status": "Approved",
            "RiskLane": "GREEN", "TTL_Hours": "24", "LatestVersion": "1.0",
            "LatestApprovedDate": "", "LatestPromptMatrixLink": "x",
            "ExamplesLink": "e", "ManifestLink": "m",
            "Tags": "truth;standards;canon",
        }
        out = normalize_row(row)
        assert out["tags"] == ["truth", "standards", "canon"]

    def test_nested_links_built(self):
        from mdpt.tools.generate_prompt_index import normalize_row

        row = {
            "CapabilityID": "CAP-TEST", "Title": "T", "Status": "Approved",
            "RiskLane": "GREEN", "TTL_Hours": "24", "LatestVersion": "1.0",
            "LatestApprovedDate": "", "LatestPromptMatrixLink": "https://pm",
            "ExamplesLink": "https://ex", "ManifestLink": "https://mf",
        }
        out = normalize_row(row)
        assert out["links"]["prompt_matrix"] == "https://pm"
        assert out["links"]["examples"] == "https://ex"
        assert out["links"]["manifest"] == "https://mf"


class TestDeterministicSort:
    def test_sorted_by_capability_id_then_version(self):
        from mdpt.tools.generate_prompt_index import sort_capabilities

        caps = [
            {"capability_id": "CAP-Z", "latest_version": "1.0"},
            {"capability_id": "CAP-A", "latest_version": "2.0"},
            {"capability_id": "CAP-A", "latest_version": "1.0"},
        ]
        result = sort_capabilities(caps)
        assert [c["capability_id"] for c in result] == ["CAP-A", "CAP-A", "CAP-Z"]
        assert result[0]["latest_version"] == "1.0"
        assert result[1]["latest_version"] == "2.0"


class TestBuildIndex:
    def test_builds_valid_index(self):
        from mdpt.tools.generate_prompt_index import build_index

        index, errors = build_index(str(CSV_FIXTURE))
        assert errors == []
        assert index["source"]["type"] == "sharepoint_list_csv"
        assert index["counts"]["total"] == 6
        assert len(index["capabilities"]) == 6

    def test_capabilities_sorted_deterministically(self):
        from mdpt.tools.generate_prompt_index import build_index

        index, _ = build_index(str(CSV_FIXTURE))
        ids = [c["capability_id"] for c in index["capabilities"]]
        assert ids == sorted(ids)

    def test_counts_have_risk_lane_breakdown(self):
        from mdpt.tools.generate_prompt_index import build_index

        index, _ = build_index(str(CSV_FIXTURE))
        by_lane = index["counts"]["by_risk_lane"]
        assert "GREEN" in by_lane
        assert sum(by_lane.values()) == 6


class TestSchemaValidation:
    def test_generated_index_validates_against_schema(self):
        import jsonschema

        from mdpt.tools.generate_prompt_index import build_index

        index, errors = build_index(str(CSV_FIXTURE))
        assert errors == []
        schema = json.loads(SCHEMA_PATH.read_text())
        jsonschema.validate(index, schema)  # raises on failure

    def test_validate_against_schema_function(self):
        from mdpt.tools.generate_prompt_index import (
            build_index,
            validate_against_schema,
        )

        index, _ = build_index(str(CSV_FIXTURE))
        schema_errors = validate_against_schema(index)
        assert schema_errors == []


class TestSummaryMarkdown:
    def test_summary_contains_totals(self):
        from mdpt.tools.generate_prompt_index import build_index, build_summary_md

        index, _ = build_index(str(CSV_FIXTURE))
        md = build_summary_md(index)
        assert "## Totals" in md
        assert "Capabilities included" in md

    def test_summary_contains_expiring_soon(self):
        from mdpt.tools.generate_prompt_index import build_index, build_summary_md

        index, _ = build_index(str(CSV_FIXTURE))
        md = build_summary_md(index)
        assert "## Expiring Soon" in md

    def test_summary_contains_top_drift(self):
        from mdpt.tools.generate_prompt_index import build_index, build_summary_md

        index, _ = build_index(str(CSV_FIXTURE))
        md = build_summary_md(index)
        assert "## Top Drift" in md
        # We know CAP-EXEC-INTEL has drift_count=5
        assert "CAP-EXEC-INTEL" in md

    def test_summary_contains_top_used(self):
        from mdpt.tools.generate_prompt_index import build_index, build_summary_md

        index, _ = build_index(str(CSV_FIXTURE))
        md = build_summary_md(index)
        assert "## Top Used" in md


class TestEndToEnd:
    def test_generate_writes_files(self, tmp_path):
        from mdpt.tools.generate_prompt_index import generate

        rc = generate(str(CSV_FIXTURE), str(tmp_path))
        assert rc == 0
        assert (tmp_path / "prompt_index.json").exists()
        assert (tmp_path / "prompt_index_summary.md").exists()

        index = json.loads((tmp_path / "prompt_index.json").read_text())
        assert index["counts"]["total"] == 6
        assert len(index["capabilities"]) == 6

    def test_generate_with_nonapproved(self, tmp_path):
        from mdpt.tools.generate_prompt_index import generate

        rc = generate(str(CSV_FIXTURE), str(tmp_path), include_nonapproved=True)
        assert rc == 0
        index = json.loads((tmp_path / "prompt_index.json").read_text())
        assert index["counts"]["total"] == 8
