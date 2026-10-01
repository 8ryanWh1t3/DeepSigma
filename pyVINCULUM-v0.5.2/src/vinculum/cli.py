from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .engine import VinculumEngine
from .ingest import ingest_file, ingest_mapping, ingest_text
from .models import ObjectType, ScoreMode


def _type(v: str) -> ObjectType:
    return ObjectType(v)


def _mode(v: str) -> ScoreMode:
    return ScoreMode(v)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vinculum", description="VINCULUM pyLib v0.5.2 — Second-Order P↔D Tension Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    score = sub.add_parser("score", help="Score text or a file")
    score.add_argument("input", help="Literal text or a path")
    score.add_argument("--type", dest="object_type", type=_type, choices=list(ObjectType), default=None)
    score.add_argument("--mode", type=_mode, choices=list(ScoreMode), default=ScoreMode.AUTO)
    score.add_argument("--id", dest="object_id", default=None)
    score.add_argument("--pretty", action="store_true")
    score.add_argument("--summary", action="store_true", help="Omit recursive child details")

    js = sub.add_parser("score-json", help="Score an episode/dataset/corpus JSON file")
    js.add_argument("path", type=Path)
    js.add_argument("--type", dest="object_type", type=_type, choices=list(ObjectType), default=ObjectType.EPISODE)
    js.add_argument("--pretty", action="store_true")
    js.add_argument("--summary", action="store_true")

    args = parser.parse_args(argv)
    engine = VinculumEngine()

    if args.command == "score":
        p = Path(args.input)
        try:
            is_file = p.exists() and p.is_file()
        except OSError:
            is_file = False
        if is_file:
            obj = ingest_file(p, object_type=args.object_type, mode=args.mode)
        else:
            typ = args.object_type or ObjectType.CLAIM
            obj = ingest_text(args.input, object_type=typ, object_id=args.object_id, mode=args.mode)
        result = engine.score(obj)
        print(json.dumps(result.to_dict(include_children=not args.summary), indent=2 if args.pretty else None, sort_keys=True))
        return 0

    if args.command == "score-json":
        data = json.loads(args.path.read_text(encoding="utf-8"))
        obj = ingest_mapping(data, object_type=args.object_type, object_id=args.path.name)
        result = engine.score(obj)
        print(json.dumps(result.to_dict(include_children=not args.summary), indent=2 if args.pretty else None, sort_keys=True))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
