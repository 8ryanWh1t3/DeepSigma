"""Local CLI. Export/review commands never execute CERPA or mutate the host."""
from __future__ import annotations

import argparse
import json
import sys

from .demo import inspection_demo
from .engine import audit, unfold
from .export import export_bundle, verify_bundle
from .model import VERSION, FoldEpisode, FoldError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="vinculum-fold", description="VINCULUM Navigable Fold add-on")
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="export the synthetic inspection episode")
    demo.add_argument("--out", required=True)
    inspect = commands.add_parser("inspect", help="audit an episode; findings are not a truth score")
    inspect.add_argument("episode")
    expand = commands.add_parser("unfold", help="recover both sides and evidence of a recorded fold")
    expand.add_argument("episode")
    expand.add_argument("fold_id")
    export = commands.add_parser("export", help="export an episode to a new sidecar directory")
    export.add_argument("episode")
    export.add_argument("--out", required=True)
    verify = commands.add_parser("verify", help="check bundle hashes and reproduce projections")
    verify.add_argument("directory")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            result = {"directory": str(export_bundle(inspection_demo(), args.out)), "synthetic": True}
        elif args.command == "inspect":
            result = audit(FoldEpisode.load(args.episode)).to_dict()
        elif args.command == "unfold":
            result = unfold(FoldEpisode.load(args.episode), args.fold_id)
        elif args.command == "export":
            result = {"directory": str(export_bundle(FoldEpisode.load(args.episode), args.out))}
        else:
            ep = verify_bundle(args.directory)
            result = {"episode_id": ep.episode_id, "digest": ep.digest, "content_consistent": True,
                      "authenticated": False}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (FoldError, OSError, KeyError, TypeError) as exc:
        print(f"vinculum-fold: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
