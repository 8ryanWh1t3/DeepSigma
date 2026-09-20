"""Outcome checks and Python/JavaScript parity for the same recorded cases."""
import copy
import csv
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('liddell_lens', ROOT / 'python/liddell_lens.py')
lens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lens)
NODE = os.environ.get('NODE') or os.environ.get('CODEX_PRIMARY_RUNTIME_NODE') or shutil.which('node')


def fixture(name='benefit'):
    return json.loads((ROOT / 'examples' / (name + '.json')).read_text(encoding='utf-8'))


class MeasurementTests(unittest.TestCase):
    def test_known_savings_include_preparation_and_review(self):
        result = lens.analyze(fixture())
        delta = result['comparison']['total_effort_minutes']
        self.assertEqual((delta['baseline'], delta['cerpa'], delta['saved']), (340, 240, 100))
        self.assertAlmostEqual(delta['percent_saved'], 100 / 340 * 100)
        self.assertEqual(result['paired_elapsed']['baseline_mean_minutes'], 250)
        self.assertEqual(result['paired_elapsed']['cerpa_mean_minutes'], 150)
        self.assertEqual(result['paired_elapsed']['percent_saved'], 40)

    def test_overhead_can_exceed_savings(self):
        result = lens.analyze(fixture('overhead'))
        self.assertEqual(result['comparison']['total_effort_minutes']['saved'], -20)
        self.assertEqual(result['comparison']['total_effort_minutes']['percent_saved'], -40)
        self.assertEqual(result['comparison']['rework_minutes']['saved'], 2)
        self.assertEqual(result['paired_elapsed']['saved_mean_minutes'], -15)

    def test_incomplete_cases_remain_in_effort_and_success_counts(self):
        result = lens.analyze(fixture('incomplete'))
        self.assertEqual(result['case_count'], 3)
        self.assertEqual(result['arms']['baseline']['completed_supported_authorized'], 1)
        self.assertEqual(result['arms']['cerpa']['completed_supported_authorized'], 2)
        self.assertEqual(result['paired_elapsed']['case_count'], 1)
        self.assertEqual(result['paired_elapsed']['excluded_case_ids'], ['POLICY-003', 'POLICY-004'])
        self.assertIsNone(result['case_results'][1]['elapsed_saved_minutes'])
        self.assertEqual(result['arms']['baseline']['total_effort_minutes'], 400)

    def test_zero_baseline_has_no_percentage(self):
        data = fixture('overhead')
        data['cases'][0]['baseline']['effort_minutes'] = dict.fromkeys(lens.CATEGORIES, 0)
        data['cases'][0]['baseline']['elapsed_minutes'] = 0
        result = lens.analyze(data)
        self.assertIsNone(result['comparison']['total_effort_minutes']['percent_saved'])
        self.assertEqual(result['comparison']['total_effort_minutes']['saved'], -70)
        self.assertIsNone(result['paired_elapsed']['percent_saved'])

    def test_no_completed_pairs_is_not_zero_elapsed(self):
        data = fixture()
        for case in data['cases']:
            case['cerpa']['authorized'] = False
        result = lens.analyze(data)
        self.assertEqual(result['paired_elapsed']['case_count'], 0)
        self.assertIsNone(result['paired_elapsed']['saved_mean_minutes'])
        self.assertEqual(result['arms']['cerpa']['completed_supported_authorized'], 0)

    def test_extreme_percentages_fail_explicitly(self):
        data=fixture('overhead')
        data['cases'][0]['baseline']['elapsed_minutes']=5e-324
        with self.assertRaisesRegex(ValueError, 'percentage exceeds finite range'):
            lens.analyze(data)
        if NODE:
            script="const e=require(process.argv[1]);let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{try{e.analyze(JSON.parse(s));process.exitCode=1;}catch(x){process.stdout.write(x.message);}});"
            proc=subprocess.run([NODE,'-e',script,str(ROOT/'js/engine.js')],input=json.dumps(data),capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn('percentage exceeds finite range',proc.stdout)

    def test_bad_measurements_are_rejected(self):
        for bad in (-1, True, None, '10', math.inf, math.nan, 1000000001):
            data = fixture()
            data['cases'][0]['baseline']['effort_minutes']['review'] = bad
            with self.subTest(value=bad), self.assertRaisesRegex(ValueError, 'review'):
                lens.analyze(data)

    def test_missing_extra_duplicate_and_flag_errors(self):
        mutations = [
            lambda d: d['cases'][0]['baseline']['effort_minutes'].pop('preparation'),
            lambda d: d['cases'][0]['cerpa'].update(authorized='true'),
            lambda d: d['cases'][0]['cerpa'].update(clarification_cycles=1.5),
            lambda d: d.update(extra='mistyped field'),
            lambda d: d['cases'].append(copy.deepcopy(d['cases'][0])),
        ]
        for mutate in mutations:
            data = fixture(); mutate(data)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                lens.analyze(data)

    def test_analysis_does_not_mutate_input(self):
        data = fixture(); before = copy.deepcopy(data)
        lens.analyze(data)
        self.assertEqual(data, before)

    def test_csv_treats_case_id_as_text(self):
        data = fixture('overhead'); data['cases'][0]['case_id'] = '=1+1'
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'cases.csv'
            lens.write_csv(lens.analyze(data), path)
            with path.open(newline='', encoding='utf-8') as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row['case_id'], "'=1+1")
            self.assertEqual(row['effort_saved_minutes'], '-20')

    def test_cli_preserves_input_and_exports_report(self):
        with tempfile.TemporaryDirectory() as td:
            input_path, report, table = [Path(td) / p for p in ('input.json', 'report.json', 'cases.csv')]
            input_path.write_text(json.dumps(fixture()), encoding='utf-8')
            before = input_path.read_bytes()
            command = [sys.executable, str(ROOT / 'python/liddell_lens.py'), str(input_path)]
            proc = subprocess.run(command + ['--output', str(input_path)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(input_path.read_bytes(), before)
            proc = subprocess.run(command + ['--output', str(report), '--csv', str(table)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(report.read_text())['case_count'], 2)
            self.assertTrue(table.is_file())

    @unittest.skipUnless(NODE, 'Node.js is needed for CLI comparison')
    def test_both_clis_preserve_hardlinks_and_escape_formula_ids(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); inp=p/'input.json'; alias=p/'alias.json'
            data=fixture('overhead'); data['cases'][0]['case_id']='\u0000=1+1'
            inp.write_text(json.dumps(data),encoding='utf-8')
            os.link(inp,alias)
            before=inp.read_bytes()
            for command in ([sys.executable,str(ROOT/'python/liddell_lens.py')],[NODE,str(ROOT/'js/cli.js')]):
                proc=subprocess.run(command+[str(inp),'--output',str(alias)],capture_output=True,text=True)
                self.assertEqual(proc.returncode,2)
                self.assertEqual(inp.read_bytes(),before)
                proc=subprocess.run(command+[str(inp),'--csv',str(p/'out.csv')],capture_output=True,text=True)
                self.assertEqual(proc.returncode,0,proc.stderr)
                with (p/'out.csv').open(newline='',encoding='utf-8') as handle:
                    row=next(csv.DictReader(handle))
                self.assertEqual(row['case_id'],"'\u0000=1+1")

    @unittest.skipUnless(NODE, 'Node.js is needed for cross-language comparison')
    def test_language_parity_examples_and_varied_records(self):
        examples = [fixture(name) for name in ('benefit', 'overhead', 'incomplete')]
        rng = random.Random(42)
        for i in range(30):
            data = fixture('overhead')
            data['data_kind'] = 'observed'
            data['title'] = 'Seeded comparison'
            for arm in ('baseline', 'cerpa'):
                run = data['cases'][0][arm]
                run['elapsed_minutes'] = rng.choice([0, rng.random() * 500])
                run['effort_minutes'] = {key: rng.random() * 100 for key in lens.CATEGORIES}
                run['clarification_cycles'] = rng.randrange(10)
                run['unresolved_contradictions'] = rng.randrange(4)
                for flag in ('closed', 'supported', 'authorized'):
                    run[flag] = rng.choice([True, False])
            examples.append(data)
        script = "const e=require(process.argv[1]); let s=''; process.stdin.on('data',c=>s+=c); process.stdin.on('end',()=>process.stdout.write(JSON.stringify(JSON.parse(s).map(e.analyze))));"
        proc = subprocess.run([NODE, '-e', script, str(ROOT / 'js/engine.js')], input=json.dumps(examples), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        js_results = json.loads(proc.stdout)

        def compare(a, b, path='$'):
            if isinstance(a, dict):
                self.assertEqual(set(a), set(b), path)
                for key in a: compare(a[key], b[key], path + '.' + key)
            elif isinstance(a, list):
                self.assertEqual(len(a), len(b), path)
                for i, (av, bv) in enumerate(zip(a, b)): compare(av, bv, f'{path}[{i}]')
            elif type(a) in (int, float):
                self.assertTrue(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-10), (path, a, b))
            else:
                self.assertEqual(a, b, path)
        for data, js in zip(examples, js_results):
            compare(lens.analyze(data), js)

    @unittest.skipUnless(NODE, 'Node.js is needed for JS validation checks')
    def test_javascript_rejects_invalid_records(self):
        invalid=[]
        for value in (True, None, -1, '10', 1000000001):
            data=fixture(); data['cases'][0]['baseline']['elapsed_minutes']=value; invalid.append(data)
        data=fixture(); data['cases'][0]['cerpa']['authorized']='false'; invalid.append(data)
        data=fixture(); data['cases'][0]['cerpa']['effort_minutes'].pop('review'); invalid.append(data)
        data=fixture(); data['cases'].append(data['cases'][0]); invalid.append(data)
        script="const e=require(process.argv[1]);let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>process.stdout.write(JSON.stringify(JSON.parse(s).map(d=>{try{e.analyze(d);return false;}catch(x){return true;}}))));"
        proc=subprocess.run([NODE,'-e',script,str(ROOT/'js/engine.js')],input=json.dumps(invalid),capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(json.loads(proc.stdout),[True]*len(invalid))


if __name__ == '__main__':
    unittest.main()
