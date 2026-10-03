"""Optional Excel evidence surface. Requires separately provisioned artifact_tool."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .assessment import Assessment, assess
from .atlas import MapView
from .exports import spreadsheet_text
from .util import ValidationError, canonical_json


def build_workbook(view: MapView, assessment: Assessment | None = None) -> Any:
    try:
        from artifact_tool import Workbook
    except ImportError as exc:
        raise ImportError("Excel export requires artifact_tool, provisioned separately. Core JSON/CSV/RDF exports require no extras.") from exc
    assessment = assessment or assess(view)
    if assessment.view_fingerprint != view.fingerprint:
        raise ValidationError("Assessment belongs to another view")
    workbook = Workbook.create()

    def tab(name: str, title: str, note: str, headers: list[str], rows: list[list[Any]]) -> Any:
        sheet = workbook.worksheets.add(name)
        width = len(headers)
        end_col = ""
        index = width
        while index:
            index, rest = divmod(index - 1, 26)
            end_col = chr(65 + rest) + end_col
        sheet.merge_cells(f"A1:{end_col}1")
        sheet.get_range("A1").values = [[title]]
        sheet.get_range("A1").format.font = {"bold": True, "size": 16}
        sheet.merge_cells(f"A2:{end_col}2")
        sheet.get_range("A2").values = [[note]]
        sheet.get_range(f"A2:{end_col}2").format.wrap_text = True
        sheet.get_range(f"A2:{end_col}2").format.row_height = 38
        sheet.get_range_by_indexes(3, 0, 1, width).values = [headers]
        sheet.get_range_by_indexes(3, 0, 1, width).format.font = {"bold": True}
        sheet.get_range_by_indexes(3, 0, 1, width).format.row_height = 30
        if rows:
            safe_rows = [[spreadsheet_text(v) for v in row] for row in rows]
            if any(isinstance(v, str) and len(v) > 32767 for row in safe_rows for v in row):
                raise ValidationError("Excel cell limit exceeded; use the lossless JSON export")
            sheet.get_range_by_indexes(4, 0, len(rows), width).values = safe_rows
        body = sheet.get_range_by_indexes(3, 0, max(2, len(rows) + 1), width)
        body.format.wrap_text = True
        body.format.vertical_alignment = "center"
        body.format.column_width = 25
        if rows:
            sheet.get_range_by_indexes(4, 0, len(rows), width).format.row_height = 48
        sheet.freeze_panes.freeze_rows(4)
        return sheet

    node_headers = ["ID", "Label", "Kind", "Layer", "Scope", "Status", "Confidence", "Evidence IDs", "Valid from", "Valid to", "Review due"]
    def node_rows(nodes: Any) -> list[list[Any]]:
        return [[n.id, n.label, n.kind, n.layer, n.scope, n.status.value, n.confidence,
                 ", ".join(n.evidence_ids), n.valid_from, n.valid_to, n.review_due] for n in nodes]

    dashboard = tab("Dashboard", "DEEP SIGMA | CARTOGRAPHY", "Recorded-map checks only. No truth, readiness, or authority certification.",
                    ["Measure", "Value", "Interpretation"], [])
    tab("C", "C | CLAIM", "Recorded claims and assumptions; status is not a truth certificate.", node_headers,
        node_rows(n for n in view.nodes if n.kind in ("claim", "assumption")))
    tab("E", "E | EVENT", "Imported event records only; no simulated execution is disguised as an observed event.", node_headers,
        node_rows(n for n in view.nodes if n.kind == "event"))
    tab("R", "R | REVIEW", "Structural findings generated from this exact view. Not a completed human review.",
        ["Finding ID", "Code", "Severity", "Subject IDs", "Detail", "Recommendation"],
        [[f.id, f.code, f.severity, ", ".join(f.subject_ids), f.detail, f.recommendation] for f in assessment.findings])
    tab("P", "P | PATCH PROPOSALS", "Recommendations only. Host COMPOSER/CERPA authority workflow must approve any change.",
        ["Finding ID", "Targets", "Status", "Proposed work"],
        [[f.id, ", ".join(f.subject_ids), "PROPOSED", f.recommendation] for f in assessment.findings])
    tab("A", "A | APPLY", "Only imported apply records appear here. Cartography never executes or authorizes APPLY.", node_headers,
        node_rows(n for n in view.nodes if n.kind == "apply"))
    tab("Memory", "MEMORY | MAP NODES", "All nodes retained in this view. Canonical JSON carries complete attributes.", node_headers, node_rows(view.nodes))
    tab("Relationships", "RELATIONSHIPS | TYPED EDGES", "Direction is stored source → target. A dependency path is not causal proof.",
        ["ID", "Source", "Predicate", "Target", "Status", "Confidence", "Evidence IDs", "Valid from", "Valid to"],
        [[e.id, e.source, e.predicate, e.target, e.status.value, e.confidence, ", ".join(e.evidence_ids), e.valid_from, e.valid_to] for e in view.edges])
    tab("Evidence", "EVIDENCE | SOURCE REGISTER", "References and recorded hashes are not proof that a source is true, trusted, or freshly verified.",
        ["ID", "Source", "Locator", "Recorded SHA-256", "Valid from", "Valid to"],
        [[e.id, e.source, e.locator, e.sha256, e.valid_from, e.valid_to] for e in view.atlas.evidence])
    tab("Legend", "LEGEND | PREDICATE CONTRACT", "Forward means source depends on target. Reverse means target depends on source. None adds no dependency semantics.",
        ["Predicate", "Label", "Definition", "Dependency", "Source kinds", "Target kinds", "Evidence relation"],
        [[p.id, p.label, p.description, p.dependency, ", ".join(p.source_kinds), ", ".join(p.target_kinds), p.evidence_relation] for p in view.atlas.predicates])
    metadata_rows = [["Atlas ID", view.atlas.id], ["As of", view.as_of], ["Source SHA-256", view.source_fingerprint],
                     ["View SHA-256", view.fingerprint], ["Assessment SHA-256", assessment.fingerprint],
                     ["Rule set", assessment.rule_set], ["Scope filter", canonical_json(view.scopes)],
                     ["Layer filter", canonical_json(view.layers)], ["Evidence required", assessment.metrics["evidence_required_nodes"]],
                     ["Live evidence references", assessment.metrics["nodes_with_live_evidence_reference"]],
                     ["Authority required", assessment.metrics["authority_required_nodes"]],
                     ["Authority references", assessment.metrics["nodes_with_authority_reference"]],
                     ["Limit", "Filters are analytical, NOT redaction or access control."],
                     ["Source", "Caller-supplied map; synthetic when marked in atlas attributes."]]
    tab("Metadata", "METADATA | REPLAY CONTEXT", "Numeric counts below are engine outputs. Dashboard ratios are spreadsheet formulas.", ["Key", "Value"], metadata_rows)
    node_end, edge_end, finding_end = max(5, len(view.nodes) + 4), max(5, len(view.edges) + 4), max(5, len(assessment.findings) + 4)
    dashboard.get_range("A5:A12").values = [["Represented nodes"], ["Represented relationships"], ["Structural findings"],
                                            ["Recorded evidence coverage"], ["Recorded authority-reference coverage"],
                                            ["As of"], ["Operational authority"], ["APPLY by this module"]]
    dashboard.get_range("B5:B9").formulas = [
        [f"=COUNTA('Memory'!A5:A{node_end})"], [f"=COUNTA('Relationships'!A5:A{edge_end})"],
        [f"=COUNTA('R'!A5:A{finding_end})"], ['=IF(Metadata!B13=0,"NOT EVALUATED",Metadata!B14/Metadata!B13)'],
        ['=IF(Metadata!B15=0,"NOT EVALUATED",Metadata!B16/Metadata!B15)']]
    dashboard.get_range("B8:B9").set_number_format("0.0%")
    dashboard.get_range("B10:B12").values = [[view.as_of], ["NOT EVALUATED"], ["NEVER"]]
    dashboard.get_range("C5:C12").values = [["Within the selected map view."], ["Typed, time-filtered edges."],
                                            ["Review conditions, not scored people."], ["Live recorded references / eligible nodes."],
                                            ["Recorded authority links / eligible nodes. Not verified grants."],
                                            ["Explicit UTC evaluation time."], ["Owned by the host authority workflow."],
                                            ["This is a read/analysis/proposal module."]]
    dashboard.get_range("A4:C12").format.wrap_text = True
    dashboard.get_range("A4:C12").format.column_width = 31
    dashboard.get_range("A5:C12").format.row_height = 46
    dashboard.get_range("A5:C12").format.vertical_alignment = "center"
    date_format = 'yyyy-mm-dd hh:mm:ss "UTC"'
    dashboard.get_range("B10").set_number_format(date_format)
    workbook.worksheets.get_item("Metadata").get_range("B6").set_number_format(date_format)
    for name in ("C", "E", "A", "Memory"):
        workbook.worksheets.get_item(name).get_range(f"I5:K{node_end}").set_number_format(date_format)
    workbook.worksheets.get_item("Relationships").get_range(f"H5:I{edge_end}").set_number_format(date_format)
    workbook.worksheets.get_item("Evidence").get_range(f"E5:F{max(5, len(view.atlas.evidence)+4)}").set_number_format(date_format)
    return workbook


def export_workbook(view: MapView, path: str | Path, assessment: Assessment | None = None) -> Path:
    from artifact_tool import SpreadsheetFile
    workbook = build_workbook(view, assessment)
    path = Path(path)
    SpreadsheetFile.export_xlsx(workbook).save(str(path))
    return path
