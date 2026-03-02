#!/usr/bin/env python3
"""Compute repo snapshot stats and inject them into README.md."""
from __future__ import annotations

import argparse
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

START_MARKER = "<!-- REPO_STATS_START -->"
END_MARKER = "<!-- REPO_STATS_END -->"

EXCLUDE_DIRS = frozenset({
    ".git", "node_modules", "dist", "build", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", "coverage", ".next",
})

MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB


def walk_repo(root: Path) -> list[Path]:
    """Yield all files, skipping excluded directories."""
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not d.startswith(".git")
        ]
        for fname in filenames:
            files.append(Path(dirpath) / fname)
    return files


def count_loc(path: Path) -> int | None:
    """Return line count for a text file, or None if binary/too large."""
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        text = path.read_bytes()
        text.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return text.count(b"\n") + (1 if text and not text.endswith(b"\n") else 0)


def is_test_file(path: Path) -> bool:
    name = path.name
    parts = path.parts
    if any(p == "tests" or p == "tests-enterprise" for p in parts):
        return name.endswith(".py")
    return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")


def compute_stats(root: Path) -> dict:
    files = walk_repo(root)
    total_files = len(files)
    total_loc = 0
    loc_by_ext: dict[str, int] = defaultdict(int)
    test_files = 0
    workflow_count = 0
    edge_html_count = 0
    pyproject_count = 0

    workflows_dir = root / ".github" / "workflows"
    if workflows_dir.is_dir():
        workflow_count = sum(
            1 for f in workflows_dir.iterdir()
            if f.suffix in (".yml", ".yaml")
        )

    for fp in files:
        rel = fp.relative_to(root)

        if is_test_file(fp):
            test_files += 1

        if fp.name == "pyproject.toml":
            pyproject_count += 1

        parts = rel.parts
        if len(parts) >= 2 and parts[0] == "edge" and fp.suffix == ".html":
            edge_html_count += 1

        loc = count_loc(fp)
        if loc is not None:
            total_loc += loc
            ext = fp.suffix.lower() or "(no ext)"
            loc_by_ext[ext] += loc

    top_exts = sorted(loc_by_ext.items(), key=lambda kv: (-kv[1], kv[0]))[:10]

    return {
        "total_files": total_files,
        "total_loc": total_loc,
        "top_extensions": top_exts,
        "workflow_count": workflow_count,
        "test_files": test_files,
        "pyproject_count": pyproject_count,
        "edge_html_count": edge_html_count,
    }


def format_number(n: int) -> str:
    return f"{n:,}"


def render_block(stats: dict) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        START_MARKER,
        f"**Repo Snapshot** (auto-generated {ts})",
        "",
        f"- **{format_number(stats['total_files'])}** files | "
        f"**{format_number(stats['total_loc'])}** lines of code",
        f"- **{stats['workflow_count']}** CI workflows | "
        f"**{stats['test_files']}** test files | "
        f"**{stats['pyproject_count']}** pyproject.toml",
        f"- **{stats['edge_html_count']}** EDGE modules",
        "",
        "LOC by extension:",
    ]
    for ext, loc in stats["top_extensions"]:
        lines.append(f"  `{ext}` {format_number(loc)}")
    lines.append(END_MARKER)
    return "\n".join(lines) + "\n"


def print_summary(stats: dict) -> None:
    print("=== Repo Snapshot Stats ===")
    print(f"  Files:        {format_number(stats['total_files'])}")
    print(f"  LOC:          {format_number(stats['total_loc'])}")
    print(f"  Workflows:    {stats['workflow_count']}")
    print(f"  Test files:   {stats['test_files']}")
    print(f"  pyproject:    {stats['pyproject_count']}")
    print(f"  EDGE modules: {stats['edge_html_count']}")
    print("  Top extensions:")
    for ext, loc in stats["top_extensions"]:
        print(f"    {ext:12s} {format_number(loc):>10s}")


def inject_readme(readme_path: Path, block: str) -> bool:
    """Replace content between markers. Returns True if file changed."""
    text = readme_path.read_text(encoding="utf-8")
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)

    if start == -1 or end == -1:
        raise SystemExit(
            f"ERROR: markers not found in {readme_path}. "
            f"Add {START_MARKER} and {END_MARKER} to the file."
        )

    end += len(END_MARKER)
    if text[end : end + 1] == "\n":
        end += 1

    new_text = text[:start] + block + text[end:]
    if new_text == text:
        return False
    readme_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute and inject repo stats")
    parser.add_argument(
        "--write-readme",
        metavar="PATH",
        help="Path to README.md to inject stats into",
    )
    parser.add_argument(
        "--root",
        metavar="DIR",
        default=".",
        help="Repo root directory (default: cwd)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    stats = compute_stats(root)
    print_summary(stats)

    if args.write_readme:
        block = render_block(stats)
        readme = Path(args.write_readme)
        if not readme.is_absolute():
            readme = root / readme
        changed = inject_readme(readme, block)
        if changed:
            print(f"\nUpdated {readme}")
        else:
            print(f"\n{readme} already up to date")


if __name__ == "__main__":
    main()
