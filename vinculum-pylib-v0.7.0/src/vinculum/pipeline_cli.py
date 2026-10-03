"""Declarative job CLI. Legacy vinculum / vinculum-lattice commands are preserved."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .pipeline import VinculumPipeline
from .version import __version__


def capabilities():
    return {'version':__version__,'core':'typed pair-owned cross-order hinges',
        'input':{'built_in':['txt','md','json','jsonl','csv','native scenario Turtle'],
                 'optional':['yaml (PyYAML)','pdf text (pypdf)','docx (python-docx)','xlsx (artifact_tool host)','parquet (pyarrow)']},
        'pairing':['manual','guided selection','explicit-policy unique exact-metadata auto'],
        'output':['JSON','CSV','Markdown','Turtle','offline HTML','optional PDF','optional host XLSX'],
        'network':'optional stateless FastAPI facade; no remote source fetch',
        'not_implemented':['live Lattice/Foundry/Vantage/OnBase connectors','generic semantic AI','production IAM','OCR','automatic command action']}


def main(argv=None):
    p=argparse.ArgumentParser(prog='vinculum-pipeline',description='VINCULUM input-runtime-output reference pipeline')
    p.add_argument('--version',action='version',version=f'VINCULUM pyLib {__version__}')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('capabilities')
    run=sub.add_parser('run');run.add_argument('job');run.add_argument('--out-dir');run.add_argument('--summary',action='store_true')
    run.add_argument('--formats',default='json,html,csv,md,ttl');run.add_argument('--strict-exit',action='store_true')
    run.add_argument('--archive',help='explicit local SQLite run archive')
    args=p.parse_args(argv)
    try:
        if args.command=='capabilities':print(json.dumps(capabilities(),indent=2));return 0
        result=VinculumPipeline().run_file(args.job)
        if args.out_dir:result.export(args.out_dir,formats=tuple(args.formats.split(',')))
        if args.archive:
            from .store import RunArchive
            with RunArchive(args.archive) as archive:archive.put(result)
        print(json.dumps(result.report.summary if args.summary else result.to_dict(),indent=2,ensure_ascii=False,allow_nan=False))
        return 2 if args.strict_exit and (result.report.summary['status']!='ALIGNED' or result.report.summary['has_gaps']) else 0
    except (ValueError,TypeError,OSError,ImportError,KeyError,OverflowError,RecursionError) as exc:
        print(f'vinculum-pipeline: {exc}',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
