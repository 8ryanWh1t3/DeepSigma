"""Portable reports and explicit optional adapters; no downstream operational writes."""
from __future__ import annotations
import csv
import hashlib
import html
import json
from pathlib import Path
from .rdf import to_turtle
from .report import html_report, write_csv, excel_safe
from .utils import canonical_json, primitive
from .version import __version__


def _delta_text(pair):
    delta=pair.discrepancy.get('signed_delta_left_unit')
    if delta is None:
        return 'not scalar' if pair.comparable else 'not evaluated'
    return str(delta)+' '+str(pair.discrepancy.get('left_unit') or '')


def _md(value):
    # No raw HTML or active Markdown from externally supplied text.
    text=html.escape(str(value),quote=True).replace('\\','\\\\')
    for character in ('*','_','[',']','`','|'):
        text=text.replace(character,'\\'+character)
    return text.replace('\n',' ')


def markdown_report(result):
    r=result.report
    lines=[f'# VINCULUM pyLib {__version__}', '## When words and numbers collide.',
        f'Graph: **{_md(r.graph_id)}**. Selected-pair status: **{r.summary["status"]}**.',
        '', 'This report evaluates representations. It does not establish physical truth, authority, safety, or permission.',
        '', '## Input -> Runtime -> Output', '', '| Stage | Execution record |','|---|---|']
    for stage in result.stage_trace:
        lines.append('| '+stage['stage']+' | '+canonical_json({k:v for k,v in stage.items() if k!='stage'}).replace('|','\\|')+' |')
    lines.extend(['','## Pair results','','| Pair | Status | Delta | Raw /100 | Supported /100 |','|---|---|---|---|---|'])
    for p in r.pairs:
        vals=[p.pair_id,p.status.value,_delta_text(p),p.raw_collision_score,p.supported_collision_score]
        lines.append('| '+' | '.join('unknown' if v is None else _md(v) for v in vals)+' |')
    lines.extend(['','## Review findings'])
    for f in result.findings:lines.append(f'- **{_md(f["category"])}**: {_md(f["reason"])}')
    lines.extend(['','## Boundaries',
        '- NOT_COMPARABLE is not CONFLICT. Missing numeric support is not zero risk.',
        '- Unpaired nodes have no collision score. Coverage concerns declared material, not every semantic fact in the original.',
        '- Auto pairing is an explicit exact-metadata policy, not unrestricted semantic understanding.',
        '- Optional origin/retreat context is attributed narrative and is not scored.',
        '',f'Job fingerprint: `{result.job_fingerprint}`. Content identity only; not a signature.'])
    return '\n'.join(lines)+'\n'


def pipeline_html(result):
    base=html_report(result.report,context=result.scenario.graph.context,codec_reports=result.codecs)
    base=base.replace('Same-side codec pairs are listed below, outside this L × M view.', 'Same-side codec pairs are listed below, outside this L × M view. A cell can summarize multiple pairs; inspect its links for individual outcomes. A cell-level UNRESOLVED summary does not imply that every pair in it has that status.')
    e=lambda x:html.escape(str(x),quote=True)
    # This uses the project-provided October navy/pale-blue pair, not a claim of
    # independently verified historic monthly Wada attribution.
    style='''<style>body{background:#A5C7D0;color:#06132F}a{color:inherit}header{padding:1.4rem;border:2px solid}th{background:#06132F;color:#A5C7D0}.stageflow{display:flex;gap:.7rem;flex-wrap:wrap}.stageflow section{border:1px solid;padding:1rem;flex:1;min-width:9rem}.tag{font-weight:bold}details{background:transparent}h3{margin-top:0}</style>'''
    stage='<h2>INPUT → RUNTIME → OUTPUT</h2><div class="stageflow">'
    for s in result.stage_trace:
        stage+='<section><h3>'+e(s['stage'])+'</h3>'+'<br>'.join(e(k.replace('_',' '))+': '+e(v) for k,v in s.items() if k!='stage')+'</section>'
    stage+='</div><p>Automatic operational actions: <strong>0</strong>. “Decide” means findings for human/application review.</p>'
    sections='<h2>Pipeline audit and review queue</h2>'+stage
    for title,value in [('Pair proposals and selection',result.pairing.to_dict()),
                        ('Review findings',result.findings),('Source identities',result.sources),
                        ('Extraction coverage and limitations',result.source_summaries),
                        ('Extraction trace',result.extraction),('Ontology normalization',result.normalization),
                        ('Higher-order support diagnostics',result.higher_order)]:
        sections+='<details><summary>'+e(title)+'</summary><pre>'+e(json.dumps(primitive(value),indent=2,ensure_ascii=False))+'</pre></details>'
    sections+='<p>Job fingerprint: <code>'+e(result.job_fingerprint)+'</code></p>'
    return base.replace('</head>',style+'</head>').replace('</body>',sections+'</body>')


def result_turtle(result):
    from rdflib import Graph,Literal,Namespace,RDF,URIRef,XSD
    ns=Namespace('urn:deep-sigma:vinculum:result:')
    g=Graph();g.bind('vr',ns)
    root=URIRef(str(ns)+result.job_fingerprint)
    g.add((root,RDF.type,ns.Evaluation))
    g.add((root,ns.version,Literal(__version__)))
    for p in result.report.pairs:
        n=URIRef(str(root)+':pair:'+hashlib.sha256(p.pair_id.encode()).hexdigest())
        g.add((root,ns.pair,n));g.add((n,RDF.type,ns.PairResult))
        g.add((n,ns.identifier,Literal(p.pair_id)));g.add((n,ns.status,Literal(p.status.value)))
        g.add((n,ns.left,Literal(p.left_id)));g.add((n,ns.right,Literal(p.right_id)))
        for prop,value in [('rawCollision',p.raw_collision_score),('supportedCollision',p.supported_collision_score)]:
            if value is not None:g.add((n,ns[prop],Literal(value,datatype=XSD.decimal)))
    return g.serialize(format='turtle')


def export_pdf(result,path):
    """Programmatic executive report; optional reportlab. No rendered source ingestion."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
    except ImportError as exc:
        raise ImportError('PDF reports require vinculum-pylib[pdf]') from exc
    from xml.sax.saxutils import escape
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle('SmallBody',parent=styles['BodyText'],fontSize=8,leading=11))
    styles['BodyText'].fontSize=10;styles['BodyText'].leading=14
    def p(t,style='BodyText'):
        return Paragraph(escape(str(t)).replace('\n','<br/>'),styles[style])
    story=[p(f'VINCULUM pyLib {__version__}','Title'),p('When words and numbers collide.','Heading2'),
           p('INPUT  >  RUNTIME  >  OUTPUT'),Spacer(1,14),p(f'Graph: {result.report.graph_id}'),
           p(f'Selected-pair status: {result.report.summary["status"]}'),
           p('Reference implementation. No truth adjudication, automatic action, or certification.'),Spacer(1,14)]
    rows=[[p(t,'SmallBody') for t in ['Pair','Status','Delta','Raw /100','Supported /100']]]
    for pair in result.report.pairs:
        vals=[pair.pair_id,pair.status.value,_delta_text(pair),pair.raw_collision_score,pair.supported_collision_score]
        rows.append([p('unknown' if x is None else x,'SmallBody') for x in vals])
    t=Table(rows,colWidths=[155,118,65,65,70],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.3,colors.HexColor('#06132F')),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#A5C7D0')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story.extend([p('Pair findings','Heading2'),t,Spacer(1,10),
        p('Unknown is not zero. Weak support does not erase a recorded discrepancy. NOT_COMPARABLE is not a numeric conflict.')])
    story.extend([PageBreak(),p('Review queue and evidence','Heading1')])
    for f in result.findings:
        story.append(p(f['category'],'Heading3'));story.append(p(f['reason']))
        if f.get('pair_id'):story.append(p('Pair: '+f['pair_id'],'SmallBody'))
    story.append(p('Source scope','Heading2'))
    for s in result.source_summaries:story.append(p(canonical_json(s),'SmallBody'))
    if not result.source_summaries:
        story.append(p(f'Typed scenario input; no source files decoded in this run. {len(result.sources)} supplied evidence references are retained in pipeline.json.','SmallBody'))
    story.extend([p('Replay identity','Heading2'),p(result.job_fingerprint,'SmallBody'),
                  p('Hash identifies content and configuration. It does not authenticate a source or establish truth.','SmallBody')])
    def footer(c,doc):
        c.saveState();c.setFont('Helvetica',8);c.drawString(40,24,'DEEP SIGMA / VINCULUM / Reference evaluation');c.drawRightString(555,24,str(doc.page));c.restoreState()
    SimpleDocTemplate(str(path),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=40,bottomMargin=40).build(story,onFirstPage=footer,onLaterPages=footer)
    return Path(path)


def export_bundle(result,directory,*,formats=('json','html','csv','md','ttl')):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    formats=tuple(formats)
    supported={'json','html','csv','md','ttl','pdf','xlsx'}
    if not formats or set(formats)-supported:raise ValueError('unsupported or empty output formats')
    paths=[]
    def write(name,text):
        p=directory/name;p.write_text(text,encoding='utf-8');paths.append(p)
    if 'json' in formats:
        write('JOB.json',json.dumps(result.replay_job,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
        write('pipeline.json',json.dumps(result.to_dict(),indent=2,ensure_ascii=False,allow_nan=False)+'\n')
        write('report.json',json.dumps(result.report.to_dict(),indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    if 'html' in formats:write('report.html',pipeline_html(result))
    if 'md' in formats:write('REPORT.md',markdown_report(result))
    if 'ttl' in formats:
        write('scenario.ttl',to_turtle(result.scenario));write('findings.ttl',result_turtle(result))
    if 'csv' in formats:
        paths.extend(write_csv(result.report,directory/'csv'))
        tables={
            'sources':[['ID','SHA-256','Locator','Basis','Parents']]+[[s.id,s.sha256,s.locator,s.basis,'; '.join(s.parents)]for s in result.sources],
            'findings':[['ID','Category','Pair','Reason']]+[[f['id'],f['category'],f.get('pair_id'),f['reason']] for f in result.findings],
            'extraction':[['Node','Source','Locator','Status','Warnings']]+[[t.node_id,t.source_id,t.locator,t.status,'; '.join(t.warnings)] for t in result.extraction]}
        for name,rows in tables.items():
            p=directory/'csv'/f'{name}.csv'
            with p.open('w',encoding='utf-8-sig',newline='') as f:csv.writer(f).writerows([[excel_safe(v) for v in row] for row in rows])
            paths.append(p)
    if 'pdf' in formats:paths.append(export_pdf(result,directory/'REPORT.pdf'))
    if 'xlsx' in formats:
        from .pipeline_excel import export_pipeline_xlsx
        paths.append(export_pipeline_xlsx(result,directory/'VINCULUM_Pipeline.xlsx'))
    manifest={str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    write('OUTPUT_MANIFEST.json',json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return tuple(paths)
