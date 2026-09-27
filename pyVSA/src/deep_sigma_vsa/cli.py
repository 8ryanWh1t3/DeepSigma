from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import VoiceSemanticAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deep-sigma-vsa",
        description="Convert a transcript into Deep Sigma candidate semantic objects.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Transcript text")
    source.add_argument("--file", type=Path, help="UTF-8 transcript file")
    parser.add_argument("--speaker", help="Speaker identifier")
    parser.add_argument("--format", choices=("json", "turtle"), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = args.text if args.text is not None else args.file.read_text(encoding="utf-8")

    packet = VoiceSemanticAdapter().from_transcript(text, speaker_id=args.speaker)
    if args.format == "turtle":
        sys.stdout.write(packet.to_turtle())
    else:
        sys.stdout.write(packet.to_json(indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
