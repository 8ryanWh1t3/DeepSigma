"""Portable JSON, CSV and accessible offline HTML reports. No network dependencies."""
from __future__ import annotations
import csv
import html
import json
from pathlib import Path
from .matrix import EvaluationReport, LANGUAGE_ORDERS, MATH_ORDERS
from .utils import canonical_json, primitive


def tables(report: EvaluationReport):
    pairs = [['Pair ID', 'Left', 'Right', 'L order', 'M order', 'Status', 'Comparable',
              'Signed delta (base unit)', 'Raw collision /100', 'Support-weighted /100',
              'Joint support', 'Alignment metadata coverage', 'Dependency warnings']]
    checks = [['Pair ID', 'Hinge order', 'Check', 'State', 'Required', 'Reason']]
    factors = [['Node ID', 'Factor', 'Order', 'Value', 'Basis', 'Source', 'Dependence group', 'Kind']]
    nodes = [['Node ID', 'Side', 'Order', 'Entity', 'Concept', 'Unit', 'Numeric range', 'P', 'D', 'Text', 'Sources', 'Dependencies']]
    for r in report.pairs:
        pairs.append([r.pair_id, r.left_id, r.right_id, r.language_order, r.mathematics_order, r.status.value,
                      r.comparable, r.discrepancy.get('signed_delta'), r.raw_collision_score,
                      r.supported_collision_score, r.support['joint_strength'], r.coverage['alignment_metadata'],
                      '; '.join(r.dependency_warnings)])
        for c in r.checks:
            checks.append([r.pair_id, c.order, c.name, c.state.value, c.required, c.reason])
    for n in report.representations:
        nodes.append([n.id, n.side.value, n.order, n.entity, n.concept, n.unit,
                      canonical_json(n.quantity) if n.quantity else None, n.pd.probabilistic, n.pd.deterministic,
                      n.text, '; '.join(n.source_ids), '; '.join(n.depends_on)])
        for f in n.support.factors:
            factors.append([n.id, f.name, f.order, f.value, f.basis, f.source_id, f.dependency_group, f.kind])
    matrix = [['L order / M order'] + [f'M{j}' for j in range(1, report.matrix['columns'] + 1)]]
    for i in range(1, report.matrix['rows'] + 1):
        matrix.append([f'L{i}'] + [c['status'] for c in report.matrix['cells'] if c['language_order'] == i])
    return {'Matrix': matrix, 'Pairs': pairs, 'Checks': checks, 'Representations': nodes, 'Support': factors}


def excel_safe(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value
    return value


def write_csv(report: EvaluationReport, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, rows in tables(report).items():
        path = directory / f'{name.lower()}.csv'
        with path.open('w', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerows([[excel_safe(v) for v in row] for row in rows])
        paths.append(path)
    return tuple(paths)


def write_json(report, path):
    data = report.to_dict() if hasattr(report, 'to_dict') else primitive(report)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return Path(path)


def html_report(report: EvaluationReport, *, context=None, codec_reports=()):
    e = lambda x: html.escape('—' if x is None else str(x), quote=True)
    def table(rows):
        head, *body = rows
        return '<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{e(v)}</th>' for v in head) + '</tr></thead><tbody>' + ''.join(
            '<tr>' + ''.join(f'<td>{e(v)}</td>' for v in row) + '</tr>' for row in body) + '</tbody></table></div>'
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
           '<title>VINCULUM — Cross-order report</title>',
           '<style>body{overflow-wrap:anywhere;box-sizing:border-box;font:16px/1.55 system-ui,sans-serif;max-width:1500px;margin:auto;padding:2rem}h1{font-size:2.6rem;line-height:1.1}h2{margin-top:2rem}table{border-collapse:collapse;font-size:.9rem;width:100%}td,th{border:1px solid;padding:.65rem;vertical-align:top;text-align:left;overflow-wrap:anywhere}th{font-weight:700}details{border:1px solid;padding:1rem;margin:.6rem 0}summary{cursor:pointer;font-weight:650}.scroll{overflow:auto}small{display:block}pre{white-space:pre-wrap;overflow-wrap:anywhere}code{font-size:.9em;overflow-wrap:anywhere}.lead{font-size:1.1rem;max-width:70ch}.matrix td{min-width:8rem}nav a{margin-right:1rem}@media print{body{padding:0}details{break-inside:avoid}.scroll{overflow:visible}}</style></head><body>',
           '<header><small>DEEP SIGMA / VINCULUM pyLib 0.7.0</small><h1>When words and numbers collide.</h1>',
           '<p class="lead">Each representation carries its own orders. A hinge exists only for a selected pair. Comparability, discrepancy, support and coverage remain separate.</p>',
           f'<p><strong>{e(report.graph_id)}</strong> · Overall: <strong>{e(report.summary["status"])}</strong> · Selected pairs: {len(report.pairs)}</p>',
           '<nav><a href="#matrix">Order matrix</a><a href="#pairs">Pair detail</a><a href="#nodes">Representations</a><a href="#boundary">Limits</a></nav></header>',
           '<h2 id="matrix">Cross-order L × M matrix</h2><p>Blank comparisons are UNPAIRED, not agreement. Same-side codec pairs are listed below, outside this L × M view.</p>']
    out.append('<div class="scroll"><table class="matrix"><thead><tr><th>L / M</th>')
    for j in range(1, report.matrix['columns'] + 1):
        out.append(f'<th>M{j}<small>{e(MATH_ORDERS.get(j, "Extension order"))}</small></th>')
    out.append('</tr></thead><tbody>')
    anchors = {p.pair_id: f'pair-{i}' for i, p in enumerate(report.pairs)}
    for i in range(1, report.matrix['rows'] + 1):
        out.append(f'<tr><th>L{i}<small>{e(LANGUAGE_ORDERS.get(i, "Extension order"))}</small></th>')
        for c in report.matrix['cells']:
            if c['language_order'] == i:
                links = '<br>'.join(f'<a href="#{anchors[p]}">{e(p)}</a>' for p in c['pair_ids'])
                out.append(f'<td><strong>{e(c["status"])}</strong><br>{links}</td>')
        out.append('</tr>')
    out.append('</tbody></table></div>')
    out.append('<h2 id="pairs">Pair-specific hinges</h2>')
    for p in report.pairs:
        out.append(f'<details id="{anchors[p.pair_id]}" open><summary>{e(p.pair_id)} — {e(p.status.value)}</summary>')
        out.append(f'<p>{e(p.left_id)} ↔ {e(p.right_id)} · Raw collision: {e(p.raw_collision_score)} /100 · Support-weighted: {e(p.supported_collision_score)} /100</p>')
        out.append('<p>Lower support does not resolve a disagreement. Missing support is not zero risk.</p>')
        out.append(table([['Check', 'Order', 'State', 'Required', 'Reason']] + [[c.name, c.order, c.state.value, c.required, c.reason] for c in p.checks]))
        out.append('<details><summary>Discrepancy, support, coverage and fingerprints</summary><pre>' + e(json.dumps(p.to_dict(), indent=2, ensure_ascii=False)) + '</pre></details></details>')
    out.append('<h2 id="nodes">Representations and higher-order factors</h2>')
    for name, rows in tables(report).items():
        if name not in {'Matrix', 'Pairs', 'Checks'}:
            out.append(f'<details><summary>{e(name)}</summary>{table(rows)}</details>')
    out.append('<details><summary>Coverage, groups and known gaps</summary><pre>' + e(json.dumps({'summary': report.summary, 'groups': report.groups}, indent=2)) + '</pre></details>')
    for c in codec_reports:
        out.append('<h2>Codec preservation audit</h2><pre>' + e(json.dumps(c.to_dict(), indent=2)) + '</pre>')
    if context:
        out.append('<h2>Optional narrative context — not scored</h2><p>' + e(context.attribution) + '</p><p><strong>Origin:</strong> ' + e(' → '.join(context.origin_path)) + '</p><p><strong>Retreat:</strong> ' + e(' → '.join(context.retreat_path)) + '</p>')
    out.append('<h2 id="boundary">Boundary</h2><p>The map is not the territory. VINCULUM tests representations. This is neither a truth oracle nor a decision or command system. Domain definitions, source reliability and selected pairings require appropriate human review. The reference monitor is not a live operational integration.</p><p>Input fingerprint: <code>' + e(report.input_fingerprint) + '</code> (content identity, not a signature)</p></body></html>')
    return ''.join(out)


def write_html(report, path, **kwargs):
    Path(path).write_text(html_report(report, **kwargs), encoding='utf-8')
    return Path(path)
