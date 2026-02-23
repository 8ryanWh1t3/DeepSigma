#!/usr/bin/env python3
"""Package MDPT Power App deployment artifacts into a .zip.

Bundles SharePoint list schemas, Power App starter kit,
PowerFx snippets, Power Automate flow template, prompt
index generator, and deployment guide into a single
distributable archive.

Usage::

    python src/mdpt/tools/package_power_app.py
    python src/mdpt/tools/package_power_app.py --out /tmp/
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MDPT = REPO / "src" / "mdpt"

# Files to include in the package
PACKAGE_FILES = [
    # Deployment guide
    ("src/mdpt/docs/power_app_deployment.md", "docs/"),
    # Power App artifacts
    (
        "src/mdpt/powerapps/STARTER_KIT.md",
        "powerapps/",
    ),
    (
        "src/mdpt/powerapps/POWERAPPS_SCREEN_MAP.md",
        "powerapps/",
    ),
    (
        "src/mdpt/powerapps/sharepoint_list_schema.json",
        "powerapps/",
    ),
    (
        "src/mdpt/powerapps/flow_scheduled_index_regen.json",
        "powerapps/",
    ),
    # PowerFx snippets
    (
        "src/mdpt/powerapps/powerfx/catalog_gallery.pfx",
        "powerapps/powerfx/",
    ),
    (
        "src/mdpt/powerapps/powerfx/filters_sort.pfx",
        "powerapps/powerfx/",
    ),
    (
        "src/mdpt/powerapps/powerfx/use_capability.pfx",
        "powerapps/powerfx/",
    ),
    (
        "src/mdpt/powerapps/powerfx/submit_run.pfx",
        "powerapps/powerfx/",
    ),
    (
        "src/mdpt/powerapps/powerfx/drift_report.pfx",
        "powerapps/powerfx/",
    ),
    (
        "src/mdpt/powerapps/powerfx/approvals_queue.pfx",
        "powerapps/powerfx/",
    ),
    # Index generator
    (
        "src/mdpt/tools/generate_prompt_index.py",
        "tools/",
    ),
    # Schema
    (
        "src/mdpt/templates/prompt_index_schema.json",
        "templates/",
    ),
]


def build_package(output_dir: Path) -> Path:
    """Build the MDPT Power App .zip package.

    Returns the path to the created archive.
    """
    stamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d",
    )
    zip_name = f"MDPT_PowerApp_Package_{stamp}.zip"
    zip_path = output_dir / zip_name

    with zipfile.ZipFile(
        zip_path, "w", zipfile.ZIP_DEFLATED,
    ) as zf:
        for src_rel, dst_prefix in PACKAGE_FILES:
            src = REPO / src_rel
            if not src.exists():
                print(
                    f"  WARN: missing {src_rel}, "
                    f"skipping",
                )
                continue
            arc_name = dst_prefix + src.name
            zf.write(src, arc_name)
            print(f"  + {arc_name}")

        # Add a manifest
        manifest = _build_manifest()
        zf.writestr("MANIFEST.txt", manifest)
        print("  + MANIFEST.txt")

    print(f"\nPackage: {zip_path}")
    print(f"Size: {zip_path.stat().st_size:,} bytes")
    return zip_path


def _build_manifest() -> str:
    """Generate a plain-text manifest."""
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "MDPT Power App Deployment Package",
        f"Generated: {now}",
        "",
        "Contents:",
    ]
    for src_rel, dst_prefix in PACKAGE_FILES:
        arc = dst_prefix + Path(src_rel).name
        lines.append(f"  {arc}")
    lines.append("  MANIFEST.txt")
    lines.append("")
    lines.append(
        "See docs/power_app_deployment.md "
        "for installation instructions.",
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Package MDPT Power App "
            "deployment artifacts"
        ),
    )
    default_out = REPO / "dist"
    parser.add_argument(
        "--out",
        type=Path,
        default=default_out,
        help=(
            "Output directory "
            f"(default: {default_out})"
        ),
    )
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    build_package(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
