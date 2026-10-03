"""Optional artifact_tool workbook. CSV remains the portable spreadsheet path."""
from pathlib import Path
from .excel import build_workbook
from .report import excel_safe
from .utils import canonical_json
from .version import __version__


def build_pipeline_workbook(result):
    wb=build_workbook(result.report)
    extra={
        'Sources':[['Source ID','SHA-256','Locator','Basis','Parents']]+[
            [s.id,s.sha256,s.locator,s.basis,'; '.join(s.parents)] for s in result.sources],
        'Extraction':[['Node ID','Source ID','Locator','Status','Warnings']]+[
            [t.node_id,t.source_id,t.locator,t.status,'; '.join(t.warnings)] for t in result.extraction],
        'Findings':[['Finding ID','Category','Pair ID','Reason']]+[
            [f['id'],f['category'],f.get('pair_id'),f['reason']] for f in result.findings],
        'Pipeline':[['Stage','Execution detail']]+[
            [s['stage'],canonical_json({k:v for k,v in s.items() if k!='stage'})] for s in result.stage_trace],
        'Pair Proposals':[['Candidate','Left','Right','State','Ambiguous','Metadata coverage','Pending','Rejected']]+[
            [c.id,c.left_id,c.right_id,c.state,c.ambiguous,c.metadata_coverage,'; '.join(c.pending),'; '.join(c.rejected)]for c in result.pairing.candidates],
    }
    for name,rows in extra.items():
        s=wb.worksheets.add(name)
        region=s.get_range_by_indexes(0,0,len(rows),len(rows[0]))
        region.values=[[excel_safe(x)for x in row]for row in rows]
        region.format.column_width=24;region.format.row_height=44;region.format.wrap_text=True
        header=s.get_range_by_indexes(0,0,1,len(rows[0]))
        header.format={'fill':'#06132F','font':{'color':'#A5C7D0','bold':True},'row_height':32}
        s.freeze_panes.freeze_rows(1)
        if name=='Findings':s.get_range(f'D1:D{len(rows)}').format.column_width=60
        if name=='Pipeline':s.get_range(f'B1:B{len(rows)}').format.column_width=75
    overview=wb.worksheets.get_item('Overview')
    overview.get_range('A1').values=[[f'VINCULUM {__version__} | INPUT > RUNTIME > OUTPUT']]
    overview.get_range('A1:F2').format.fill='#06132F'
    overview.get_range('A1:F2').format.font.color='#A5C7D0'
    overview.get_range('A12:B16').values=[['Additional measure','Value'],['Partial overlaps',None],
        ['Aligned pairs',None],['Review findings',None],['Registered sources',None]]
    end=max(2,len(result.report.pairs)+1)
    overview.get_range('B13:B16').formulas=[
        [f'=COUNTIF(Pairs!F2:F{end},"PARTIAL")'],[f'=COUNTIF(Pairs!F2:F{end},"ALIGNED")'],
        [f'=COUNTA(Findings!A2:A{max(2,len(result.findings)+1)})'],
        [f'=COUNTA(Sources!A2:A{max(2,len(result.sources)+1)})']]
    # Derived score cells are formulas over preserved engine outputs and support.
    if result.report.pairs:
        pairs=wb.worksheets.get_item('Pairs')
        pairs.get_range('J2').formulas=[['=IF(OR(I2="",K2=""),"",I2*K2)']]
        if len(result.report.pairs)>1:pairs.get_range(f'J2:J{len(result.report.pairs)+1}').fill_down()
    return wb


def export_pipeline_xlsx(result,path):
    from artifact_tool import SpreadsheetFile
    book=build_pipeline_workbook(result)
    SpreadsheetFile.export_xlsx(book).save(str(path))
    return Path(path)
