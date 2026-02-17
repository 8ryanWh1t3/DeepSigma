#!/usr/bin/env python3
"""
tools/exhaust_cli.py – CLI for the Exhaust Inbox system
========================================================
Commands:
    import   – Import a JSONL file of events
    assemble – Assemble events into episodes
    refine   – Refine an episode (extract truth/reasoning/memory)
    commit   – Commit a refined episode
    list     – List episodes with optional filters
    health   – Check API health

Usage:
    python tools/exhaust_cli.py import --file specs/sample_episode_events.jsonl
    python tools/exhaust_cli.py assemble
    python tools/exhaust_cli.py list
    python tools/exhaust_cli.py refine --episode <episode_id>
    python tools/exhaust_cli.py commit --episode <episode_id>
    python tools/exhaust_cli.py health
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_BASE = "http://localhost:8000/api/exhaust"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _request(
    path: str,
    method: str = "GET",
    body: Optional[Any] = None,
    base: str = DEFAULT_BASE,
) -> Dict[str, Any]:
    url = f"{base}{path}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode() if exc.fp else ""
        print(f"ERROR {exc.code}: {err_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Connection failed: {exc.reason}", file=sys.stderr)
        print(f"Is the server running at {base}?", file=sys.stderr)
        sys.exit(1)


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_import(args: argparse.Namespace) -> None:
    """Import events from a JSONL file."""
    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    events = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"Warning: skipping line {i}: {exc}", file=sys.stderr)

    if not events:
        print("No events found in file.", file=sys.stderr)
        sys.exit(1)

    result = _request("/events", method="POST", body=events, base=args.base)
    print(f"Ingested {result.get('ingested', '?')} events.")
    _print_json(result)


def cmd_assemble(args: argparse.Namespace) -> None:
    """Assemble ingested events into episodes."""
    result = _request("/episodes/assemble", method="POST", base=args.base)
    print(f"Assembled {result.get('assembled', '?')} episodes.")
    _print_json(result)


def cmd_list(args: argparse.Namespace) -> None:
    """List episodes with optional filters."""
    params = []
    if args.project:
        params.append(f"project={args.project}")
    if args.team:
        params.append(f"team={args.team}")
    if args.source:
        params.append(f"source={args.source}")
    if args.drift_only:
        params.append("drift_only=true")
    if args.limit:
        params.append(f"limit={args.limit}")

    qs = "?" + "&".join(params) if params else ""
    result = _request(f"/episodes{qs}", base=args.base)

    episodes = result.get("episodes", [])
    total = result.get("total", len(episodes))
    print(f"Episodes: {total}")
    print("-" * 70)

    for ep in episodes:
        eid = ep.get("episode_id", "?")[:12]
        proj = ep.get("project", "—")
        team = ep.get("team", "")
        score = ep.get("coherence_score", 0)
        grade = ep.get("grade", "?")
        drift = len(ep.get("drift_signals", []))
        evts = len(ep.get("events", []))
        committed = "✓" if ep.get("committed") else " "
        print(
            f"  [{committed}] {eid}  {proj:15s}  {team:10s}  "
            f"score={score:3.0f} ({grade})  drift={drift}  events={evts}"
        )


def cmd_refine(args: argparse.Namespace) -> None:
    """Refine a specific episode."""
    result = _request(
        f"/episodes/{args.episode}/refine", method="POST", base=args.base
    )
    print(f"Refined episode {args.episode[:12]}…")
    truth = len(result.get("truth", []))
    reasoning = len(result.get("reasoning", []))
    memory = len(result.get("memory", []))
    score = result.get("coherence_score", 0)
    grade = result.get("grade", "?")
    print(
        f"  truth={truth}  reasoning={reasoning}  memory={memory}  "
        f"score={score} ({grade})"
    )
    _print_json(result)


def cmd_commit(args: argparse.Namespace) -> None:
    """Commit a refined episode."""
    result = _request(
        f"/episodes/{args.episode}/commit", method="POST", base=args.base
    )
    if result.get("committed"):
        print(f"Committed episode {args.episode[:12]}… ✓")
    else:
        print(f"Commit response:")
        _print_json(result)


def cmd_health(args: argparse.Namespace) -> None:
    """Check API health."""
    result = _request("/health", base=args.base)
    _print_json(result)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="exhaust_cli",
        description="CLI for the DeepSigma Exhaust Inbox system",
    )
    parser.add_argument(
        "--base", "-b", default=DEFAULT_BASE, help="API base URL"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # import
    p_import = sub.add_parser("import", help="Import events from JSONL file")
    p_import.add_argument("--file", "-f", required=True, help="Path to JSONL")
    p_import.set_defaults(func=cmd_import)

    # assemble
    p_assemble = sub.add_parser("assemble", help="Assemble events into episodes")
    p_assemble.set_defaults(func=cmd_assemble)

    # list
    p_list = sub.add_parser("list", help="List episodes")
    p_list.add_argument("--project", "-p", default=None)
    p_list.add_argument("--team", "-t", default=None)
    p_list.add_argument("--source", "-s", default=None)
    p_list.add_argument("--drift-only", action="store_true")
    p_list.add_argument("--limit", "-l", type=int, default=None)
    p_list.set_defaults(func=cmd_list)

    # refine
    p_refine = sub.add_parser("refine", help="Refine an episode")
    p_refine.add_argument("--episode", "-e", required=True, help="Episode ID")
    p_refine.set_defaults(func=cmd_refine)

    # commit
    p_commit = sub.add_parser("commit", help="Commit a refined episode")
    p_commit.add_argument("--episode", "-e", required=True, help="Episode ID")
    p_commit.set_defaults(func=cmd_commit)

    # health
    p_health = sub.add_parser("health", help="Check API health")
    p_health.set_defaults(func=cmd_health)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
