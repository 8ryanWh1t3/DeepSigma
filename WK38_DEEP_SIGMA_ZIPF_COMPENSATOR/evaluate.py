#!/usr/bin/env python3
"""Evaluate a local JSON scenario without starting the browser console."""
import argparse
import json
from pathlib import Path
from deep_sigma_zipf.engine import evaluate, ValidationError
from run import strict_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('scenario', nargs='?', default=str(Path(__file__).parent / 'data' / 'demo.json'))
    p.add_argument('--output', type=Path)
    p.add_argument('--budget', type=int)
    p.add_argument('--as-of', help='Explicit scenario timestamp YYYY-MM-DDTHH:MM:SSZ')
    args = p.parse_args()
    try:
        payload = strict_json(Path(args.scenario).read_text(encoding='utf-8'))
        if not isinstance(payload, dict):
            raise ValueError('Scenario must be a JSON object.')
        if args.budget is not None:
            payload['review_budget'] = args.budget
        if args.as_of is not None:
            payload['as_of'] = args.as_of
        result = evaluate(payload)
        text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        if args.output:
            args.output.write_text(text, encoding='utf-8')
            print(f'Saved simulated evaluation to {args.output}')
        else:
            print(text, end='')
    except (OSError, ValueError, ValidationError) as exc:
        p.exit(1, f'Evaluation failed: {exc}\n')


if __name__ == '__main__':
    main()
