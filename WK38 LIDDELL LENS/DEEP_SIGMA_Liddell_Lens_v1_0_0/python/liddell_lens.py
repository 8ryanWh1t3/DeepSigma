#!/usr/bin/env python3
"""DEEP SIGMA Liddell Lens 1.0.0: transparent paired workflow measurements.

Standard library only. Imported records are observations, not proof of causation.
Preparation and review are included in total effort, never treated as free.
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys

CATEGORIES = ('preparation', 'execution', 'review', 'clarification', 'rework')
ROOT_KEYS = ('schema_version', 'data_kind', 'title', 'cases')
RUN_KEYS = ('elapsed_minutes', 'effort_minutes', 'clarification_cycles',
            'unresolved_contradictions', 'closed', 'supported', 'authorized')
CSV_FIELDS = ('case_id', 'baseline_complete', 'cerpa_complete',
              'baseline_effort_minutes', 'cerpa_effort_minutes',
              'effort_saved_minutes', 'baseline_elapsed_minutes',
              'cerpa_elapsed_minutes', 'elapsed_saved_minutes')
# Match ECMAScript String.trim for consistent validation across both engines.
TRIM_CHARS = '\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff'


def _object(value, keys, path):
    if not isinstance(value, dict):
        raise ValueError(f'{path}: expected an object')
    missing = set(keys) - set(value)
    extra = set(value) - set(keys)
    if missing:
        raise ValueError(f'{path}: missing fields: {", ".join(sorted(missing))}')
    if extra:
        raise ValueError(f'{path}: unknown fields: {", ".join(map(str, sorted(extra, key=str)))}')


def _string(value, path):
    if not isinstance(value, str) or not value or len(value) > 200 or value != value.strip(TRIM_CHARS):
        raise ValueError(f'{path}: expected a nonempty trimmed string of at most 200 characters')


def _number(value, path, integer=False):
    limit = 1000000 if integer else 1000000000
    if (type(value) not in (int, float) or value < 0 or value > limit
            or not math.isfinite(value) or (integer and value != int(value))):
        kind = 'integer' if integer else 'finite number'
        raise ValueError(f'{path}: expected {kind} between 0 and {limit}')


def validate(data):
    """Raise ValueError with a field path for invalid or incomplete data."""
    _object(data, ROOT_KEYS, '$')
    if data['schema_version'] != '1.0':
        raise ValueError('$.schema_version: expected "1.0"')
    if data['data_kind'] not in ('illustrative', 'observed'):
        raise ValueError('$.data_kind: expected "illustrative" or "observed"')
    _string(data['title'], '$.title')
    if not isinstance(data['cases'], list) or not 1 <= len(data['cases']) <= 10000:
        raise ValueError('$.cases: expected 1 to 10000 paired cases')
    seen = set()
    for i, case in enumerate(data['cases']):
        path = f'$.cases[{i}]'
        _object(case, ('case_id', 'baseline', 'cerpa'), path)
        _string(case['case_id'], path + '.case_id')
        if case['case_id'] in seen:
            raise ValueError(path + '.case_id: duplicate case ID')
        seen.add(case['case_id'])
        for arm in ('baseline', 'cerpa'):
            run, rp = case[arm], path + '.' + arm
            _object(run, RUN_KEYS, rp)
            _number(run['elapsed_minutes'], rp + '.elapsed_minutes')
            _object(run['effort_minutes'], CATEGORIES, rp + '.effort_minutes')
            for category in CATEGORIES:
                _number(run['effort_minutes'][category], rp + '.effort_minutes.' + category)
            for count in ('clarification_cycles', 'unresolved_contradictions'):
                _number(run[count], rp + '.' + count, integer=True)
            for flag in ('closed', 'supported', 'authorized'):
                if type(run[flag]) is not bool:
                    raise ValueError(rp + '.' + flag + ': expected a boolean')


def _complete(run):
    return run['closed'] and run['supported'] and run['authorized']


def _percent(baseline, cerpa):
    if baseline == 0:
        return None
    value = (baseline - cerpa) / baseline * 100
    if not math.isfinite(value):
        raise ValueError('Calculated percentage exceeds finite range')
    return value


def _delta(baseline, cerpa):
    saved = baseline - cerpa
    return {'baseline': baseline, 'cerpa': cerpa, 'saved': saved,
            'percent_saved': _percent(baseline, cerpa)}


def analyze(data):
    """Compare recorded baseline and CERPA runs without mutating input.

    Completion timing uses only pairs that are closed, supported and authorized
    in BOTH arms. All cases remain included in effort and completion counts.
    """
    validate(data)
    n = len(data['cases'])
    arms = {}
    for arm in ('baseline', 'cerpa'):
        runs = [case[arm] for case in data['cases']]
        effort = {category: sum(run['effort_minutes'][category] for run in runs)
                  for category in CATEGORIES}
        completed = sum(_complete(run) for run in runs)
        arms[arm] = {
            'case_count': n,
            'completed_supported_authorized': completed,
            'completion_rate_pct': completed / n * 100,
            'total_effort_minutes': sum(effort.values()),
            'effort_minutes': effort,
            'clarification_cycles': sum(run['clarification_cycles'] for run in runs),
            'unresolved_contradictions': sum(run['unresolved_contradictions'] for run in runs),
        }
    b, c = arms['baseline'], arms['cerpa']
    comparison = {
        'total_effort_minutes': _delta(b['total_effort_minutes'], c['total_effort_minutes']),
        'rework_minutes': _delta(b['effort_minutes']['rework'], c['effort_minutes']['rework']),
        'clarification_cycles': _delta(b['clarification_cycles'], c['clarification_cycles']),
        'unresolved_contradictions': _delta(b['unresolved_contradictions'], c['unresolved_contradictions']),
    }
    eligible, excluded, rows = [], [], []
    for case in data['cases']:
        rb, rc = case['baseline'], case['cerpa']
        bc, cc = _complete(rb), _complete(rc)
        be, ce = sum(rb['effort_minutes'].values()), sum(rc['effort_minutes'].values())
        (eligible if bc and cc else excluded).append(case if bc and cc else case['case_id'])
        rows.append({
            'case_id': case['case_id'], 'baseline_complete': bc, 'cerpa_complete': cc,
            'baseline_effort_minutes': be, 'cerpa_effort_minutes': ce,
            'effort_saved_minutes': be - ce,
            'baseline_elapsed_minutes': rb['elapsed_minutes'],
            'cerpa_elapsed_minutes': rc['elapsed_minutes'],
            'elapsed_saved_minutes': rb['elapsed_minutes'] - rc['elapsed_minutes'] if bc and cc else None,
        })
    bn = sum(case['baseline']['elapsed_minutes'] for case in eligible) / len(eligible) if eligible else None
    cn = sum(case['cerpa']['elapsed_minutes'] for case in eligible) / len(eligible) if eligible else None
    warnings = ['Recorded support and authority flags are human assessments; this tool does not verify evidence or authorization.']
    if data['data_kind'] == 'illustrative':
        warnings.append('ILLUSTRATIVE DATA: these results are examples, not measured Deep Sigma performance.')
    if excluded:
        warnings.append('Elapsed-time comparison excludes cases without a closed, supported, authorized decision in both arms; inspect completion counts and excluded cases.')
    warnings.append('Observed differences do not establish causation. Use comparable cases and include all preparation, review, and collection costs in the evaluation.')
    return {
        'schema_version': '1.0', 'data_kind': data['data_kind'], 'title': data['title'], 'case_count': n,
        'arms': arms, 'comparison': comparison,
        'paired_elapsed': {
            'case_count': len(eligible), 'excluded_case_ids': excluded,
            'baseline_mean_minutes': bn, 'cerpa_mean_minutes': cn,
            'saved_mean_minutes': bn - cn if eligible else None,
            'percent_saved': _percent(bn, cn) if eligible else None,
        },
        'case_results': rows, 'warnings': warnings,
    }


def _csv_cell(value):
    if value is None:
        return ''
    if type(value) is bool:
        return 'true' if value else 'false'
    # Spreadsheet export must not execute imported case IDs as formulas.
    if isinstance(value, str) and value.lstrip(TRIM_CHARS + ''.join(chr(i) for i in range(32))).startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def write_csv(result, path):
    with Path(path).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows({key: _csv_cell(row[key]) for key in CSV_FIELDS}
                         for row in result['case_results'])


def main(argv=None):
    parser = argparse.ArgumentParser(description='DEEP SIGMA Liddell Lens: compare baseline and CERPA observations.')
    parser.add_argument('input', type=Path, help='Input JSON observations')
    parser.add_argument('--output', type=Path, help='Write result JSON instead of stdout')
    parser.add_argument('--csv', type=Path, help='Write per-case CSV for Excel')
    args = parser.parse_args(argv)
    try:
        paths = [path.resolve() for path in (args.input, args.output, args.csv) if path is not None]
        if len(paths) != len(set(paths)):
            raise ValueError('Input, JSON output and CSV output must be different files')
        for i, left in enumerate(paths):
            for right in paths[i + 1:]:
                if left.exists() and right.exists() and os.path.samefile(left, right):
                    raise ValueError('Input, JSON output and CSV output must be different files')
        data = json.loads(args.input.read_text(encoding='utf-8'))
        result = analyze(data)
        rendered = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        if args.output:
            args.output.write_text(rendered, encoding='utf-8')
        else:
            sys.stdout.write(rendered)
        if args.csv:
            write_csv(result, args.csv)
    except (OSError, ValueError, TypeError) as exc:
        print(f'Liddell Lens: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
