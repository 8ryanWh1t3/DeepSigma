"""deepsigma new-connector — scaffold a ConnectorV1 plugin."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "connector"


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    if not s:
        raise ValueError("Connector name must contain letters or numbers")
    return s


def _class_name(slug: str) -> str:
    return "".join(part.capitalize() for part in slug.split("_")) + "Connector"


def _render(text: str, context: dict[str, str]) -> str:
    out = text
    for key, value in context.items():
        out = out.replace("{{ " + key + " }}", value)
    return out


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("new-connector", help="Scaffold a ConnectorV1 plugin")
    p.add_argument("name", help="Connector name (e.g. csv, zendesk, my-api)")
    p.add_argument("--out-dir", default="src/adapters", help="Base output directory")
    p.add_argument("--tests-dir", default="tests", help="Directory for generated test file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    slug = _slug(args.name)
    class_name = _class_name(slug)
    base = Path(args.out_dir).resolve()
    target = base / slug
    tests_dir = Path(args.tests_dir).resolve()

    target.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    import_path = f"adapters.{slug}.connector"
    context = {
        "connector_slug": slug,
        "connector_class": class_name,
        "import_path": import_path,
    }

    mappings = {
        "connector.py.tpl": target / "connector.py",
        "mcp_tools.py.tpl": target / "mcp_tools.py",
        "README.md.tpl": target / "README.md",
        "test_connector.py.tpl": tests_dir / f"test_{slug}_connector.py",
    }

    for src_name, dst in mappings.items():
        src = _TEMPLATE_DIR / src_name
        rendered = _render(src.read_text(encoding="utf-8"), context)
        dst.write_text(rendered, encoding="utf-8")

    init_file = target / "__init__.py"
    if not init_file.exists():
        init_file.write_text("\n", encoding="utf-8")

    print(f"Created connector scaffold: {target}")
    print(f"Created test scaffold: {tests_dir / f'test_{slug}_connector.py'}")
    return 0
