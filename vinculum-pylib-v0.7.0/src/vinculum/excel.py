"""Optional XLSX adapter for environments with artifact_tool.

CSV/JSON/HTML need no spreadsheet runtime. artifact_tool is not installed automatically
by this package; this adapter is useful in artifact-enabled authoring environments.
"""
from pathlib import Path
from .report import tables, excel_safe


def build_workbook(report):
    try:
        from artifact_tool import Workbook
    except ImportError as exc:
        raise RuntimeError('XLSX export requires the artifact_tool spreadsheet runtime; use write_csv for portable Excel-compatible tables') from exc
    wb = Workbook.create()
    summary = wb.worksheets.add('Overview')
    summary.merge_cells('A1:F1')
    summary.get_range('A1').values = [['VINCULUM 0.7.0 — Cross-order hinge report']]
    summary.get_range('A1:F1').format.font.bold = True
    summary.get_range('A1:F1').format.row_height = 30
    summary.merge_cells('A2:F2')
    summary.get_range('A2').values = [['Scores describe selected representations, not truth, risk or permission.']]
    summary.get_range('A2:F2').format.wrap_text = True
    summary.get_range('A4:B10').values = [
        ['Measure', 'Value'], ['Selected pairs', None], ['Conflicts', None], ['Unresolved', None],
        ['Not comparable', None], ['Unpaired material nodes', len(report.summary['unpaired_material_nodes'])],
        ['Input fingerprint', report.input_fingerprint],
    ]
    summary.get_range('A1:A10').format.column_width = 32
    summary.get_range('B1:F10').format.column_width = 18
    summary.get_range('B10:F10').merge()
    summary.get_range('B10').format.wrap_text = True
    n = len(report.pairs)
    end = max(2, n + 1)
    summary.get_range('B5:B8').formulas = [
        [f'=COUNTA(Pairs!A2:A{end})'],
        [f'=COUNTIF(Pairs!F2:F{end},"CONFLICT")'],
        [f'=COUNTIF(Pairs!F2:F{end},"UNRESOLVED")'],
        [f'=COUNTIF(Pairs!F2:F{end},"NOT_COMPARABLE")'],
    ]
    for name, rows in tables(report).items():
        s = wb.worksheets.add(name)
        rows = [[excel_safe(v) for v in row] for row in rows]
        s.get_range_by_indexes(0, 0, len(rows), len(rows[0])).values = rows
        used = s.get_range_by_indexes(0, 0, len(rows), len(rows[0]))
        used.format.column_width = 22
        used.format.row_height = 60
        used.format.wrap_text = True
        s.get_range_by_indexes(0, 0, 1, len(rows[0])).format.font.bold = True
        s.get_range_by_indexes(0, 0, 1, len(rows[0])).format.row_height = 40
        s.freeze_panes.freeze_rows(1)
        if name == 'Pairs' and len(rows) > 1:
            s.get_range(f'I2:K{len(rows)}').set_number_format('0.0000')
            s.get_range(f'L2:L{len(rows)}').set_number_format('0.0%')
        if name == 'Checks':
            s.get_range(f'F1:F{len(rows)}').format.column_width = 40
        if name == 'Support':
            s.get_range(f'E1:E{len(rows)}').format.column_width = 40
        if name == 'Representations':
            s.get_range(f'J1:J{len(rows)}').format.column_width = 40
        if name == 'Matrix':
            used.format.column_width = 25
            used.format.row_height = 48
    return wb


def export_xlsx(report, path):
    from artifact_tool import SpreadsheetFile
    wb = build_workbook(report)
    SpreadsheetFile.export_xlsx(wb).save(str(path))
    return Path(path)
