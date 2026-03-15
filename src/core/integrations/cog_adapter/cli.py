"""COG Adapter CLI — wire into ``coherence cog`` subparser group."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_cog_import(args: argparse.Namespace) -> None:
    """Import a COG bundle and display as DeepSigma artifact."""
    from .importer import cog_to_deepsigma, load_cog_bundle

    path = args.file
    if not Path(path).exists():
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    bundle = load_cog_bundle(path)
    artifact = cog_to_deepsigma(bundle)

    if getattr(args, "json_output", False):
        print(json.dumps(artifact.to_dict(), indent=2))
    else:
        print(f"COG Import | bundle: {bundle.manifest.bundle_id}")
        print(f"  Version:    {bundle.manifest.version}")
        print(f"  Artifacts:  {len(bundle.artifacts)}")
        print(f"  Proof:      {'present' if bundle.proof else 'none'}")
        print(f"  Replay:     {len(bundle.replay_steps)} steps")
        print()
        print("Mapped to DeepSigma:")
        print(f"  Truth claims:      {len(artifact.truth_claims)}")
        print(f"  Reasoning:         {'present' if artifact.reasoning else 'none'}")
        print(f"  Memory refs:       {len(artifact.memory_refs)}")
        print(f"  Drift annotations: {len(artifact.drift_annotations)}")
        print(f"  Patch refs:        {len(artifact.patch_refs)}")
        print(f"  Receipt:           {'present' if artifact.receipt else 'none'}")


def cmd_cog_export(args: argparse.Namespace) -> None:
    """Export a DeepSigma artifact JSON as a COG bundle."""
    from .exporter import deepsigma_to_cog, write_cog_bundle
    from .models import DeepSigmaDecisionArtifact

    artifact_path = args.artifact
    if not Path(artifact_path).exists():
        print(f"Error: {artifact_path} not found", file=sys.stderr)
        sys.exit(1)

    data = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    artifact = DeepSigmaDecisionArtifact.from_dict(data)
    bundle = deepsigma_to_cog(artifact)

    output = args.output
    write_cog_bundle(bundle, output)

    if getattr(args, "json_output", False):
        print(json.dumps(bundle.to_dict(), indent=2))
    else:
        print(f"COG Export | artifact: {artifact.artifact_id}")
        print(f"  Bundle ID:  {bundle.manifest.bundle_id}")
        print(f"  Artifacts:  {len(bundle.artifacts)}")
        print(f"  Written to: {output}")


def cmd_cog_verify(args: argparse.Namespace) -> None:
    """Verify a COG bundle for integrity and completeness."""
    from .importer import load_cog_bundle
    from .verifier import verify_cog_bundle

    path = args.file
    if not Path(path).exists():
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    bundle = load_cog_bundle(path)
    result = verify_cog_bundle(bundle)

    if getattr(args, "json_output", False):
        print(json.dumps(result, indent=2))
    else:
        status = result["status"].upper()
        print(f"COG Verify | bundle: {bundle.manifest.bundle_id}")
        print(f"  Status:              {status}")
        print(f"  Bundle hash:         {'present' if result['bundle_hash_present'] else 'missing'}")
        print(f"  Proof metadata:      {'present' if result['proof_metadata_present'] else 'missing'}")
        print(f"  Replay metadata:     {'present' if result['replay_metadata_present'] else 'missing'}")
        print(f"  Manifest consistent: {'yes' if result['manifest_consistent'] else 'no'}")
        print(f"  Content hashes:      {'valid' if result['content_hash_valid'] else 'INVALID'}")
        if result["missing_required_fields"]:
            print(f"  Missing fields:      {', '.join(result['missing_required_fields'])}")
        if result["issues"]:
            for issue in result["issues"]:
                print(f"  Issue: {issue}")

    sys.exit(0 if result["status"] == "pass" else 1)


def cmd_cog_diff(args: argparse.Namespace) -> None:
    """Compare two COG bundles and show differences."""
    from .diff import diff_cog_bundles
    from .importer import load_cog_bundle

    for f in (args.file1, args.file2):
        if not Path(f).exists():
            print(f"Error: {f} not found", file=sys.stderr)
            sys.exit(1)

    before = load_cog_bundle(args.file1)
    after = load_cog_bundle(args.file2)
    diff = diff_cog_bundles(before, after)

    if getattr(args, "json_output", False):
        print(json.dumps(diff.to_dict(), indent=2))
    else:
        print(f"COG Diff | {diff.from_bundle_id} -> {diff.to_bundle_id}")
        print(f"  Added:    {len(diff.added_artifacts)}")
        print(f"  Removed:  {len(diff.removed_artifacts)}")
        print(f"  Modified: {len(diff.modified_artifacts)}")
        if diff.manifest_changes:
            print(f"  Manifest: {list(diff.manifest_changes.keys())}")
        if diff.proof_changes:
            print(f"  Proof:    {list(diff.proof_changes.keys())}")
        if diff.replay_changes:
            print(f"  Replay:   {list(diff.replay_changes.keys())}")
        for a in diff.added_artifacts:
            print(f"  + {a['refId']} ({a['refType']})")
        for r in diff.removed_artifacts:
            print(f"  - {r['refId']} ({r['refType']})")
        for m in diff.modified_artifacts:
            print(f"  ~ {m['refId']} ({m['refType']})")


def cmd_cog_batch_import(args: argparse.Namespace) -> None:
    """Import all COG bundles from a directory."""
    from .batch import batch_import_cog_bundles

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    paths = sorted(str(p) for p in directory.glob("*.json"))
    if not paths:
        print(f"No JSON files found in {directory}", file=sys.stderr)
        sys.exit(1)

    result = batch_import_cog_bundles(paths)

    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"COG Batch Import | {result.succeeded}/{result.total} succeeded")
        if result.errors:
            for err in result.errors:
                print(f"  Error: {err}")


def cmd_cog_merge(args: argparse.Namespace) -> None:
    """Merge multiple COG bundles into one."""
    from .batch import merge_bundles
    from .exporter import write_cog_bundle
    from .importer import load_cog_bundle

    for f in args.bundles:
        if not Path(f).exists():
            print(f"Error: {f} not found", file=sys.stderr)
            sys.exit(1)

    bundles = [load_cog_bundle(f) for f in args.bundles]
    merged = merge_bundles(bundles)

    output = args.output
    write_cog_bundle(merged, output)

    if getattr(args, "json_output", False):
        print(json.dumps(merged.to_dict(), indent=2))
    else:
        print(f"COG Merge | {len(bundles)} bundles -> {merged.manifest.bundle_id}")
        print(f"  Artifacts:  {len(merged.artifacts)}")
        print(f"  Written to: {output}")


def register_cog_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register COG adapter subcommands on the core CLI."""
    p_cog = subparsers.add_parser("cog", help="COG bundle adapter operations")
    cog_sub = p_cog.add_subparsers(dest="cog_command", required=True)

    # coherence cog import <file>
    p_import = cog_sub.add_parser("import", help="Import a COG bundle")
    p_import.add_argument("file", help="Path to COG bundle JSON file")
    p_import.add_argument("--json", action="store_true", dest="json_output",
                          help="Output as JSON")
    p_import.set_defaults(func=cmd_cog_import)

    # coherence cog export --artifact <file> <output>
    p_export = cog_sub.add_parser("export", help="Export artifact as COG bundle")
    p_export.add_argument("--artifact", required=True,
                          help="Path to DeepSigma artifact JSON")
    p_export.add_argument("output", help="Output path for COG bundle JSON")
    p_export.add_argument("--json", action="store_true", dest="json_output",
                          help="Output as JSON")
    p_export.set_defaults(func=cmd_cog_export)

    # coherence cog verify <file>
    p_verify = cog_sub.add_parser("verify", help="Verify a COG bundle")
    p_verify.add_argument("file", help="Path to COG bundle JSON file")
    p_verify.add_argument("--json", action="store_true", dest="json_output",
                          help="Output as JSON")
    p_verify.set_defaults(func=cmd_cog_verify)

    # coherence cog diff <file1> <file2>
    p_diff = cog_sub.add_parser("diff", help="Compare two COG bundles")
    p_diff.add_argument("file1", help="Path to first bundle")
    p_diff.add_argument("file2", help="Path to second bundle")
    p_diff.add_argument("--json", action="store_true", dest="json_output",
                        help="Output as JSON")
    p_diff.set_defaults(func=cmd_cog_diff)

    # coherence cog batch-import <directory>
    p_batch = cog_sub.add_parser("batch-import",
                                 help="Import all COG bundles from a directory")
    p_batch.add_argument("directory", help="Directory containing bundle JSON files")
    p_batch.add_argument("--json", action="store_true", dest="json_output",
                         help="Output as JSON")
    p_batch.set_defaults(func=cmd_cog_batch_import)

    # coherence cog merge <bundles...> <output>
    p_merge = cog_sub.add_parser("merge",
                                 help="Merge multiple COG bundles into one")
    p_merge.add_argument("bundles", nargs="+", help="Bundle JSON files to merge")
    p_merge.add_argument("--output", "-o", required=True,
                         help="Output path for merged bundle")
    p_merge.add_argument("--json", action="store_true", dest="json_output",
                         help="Output as JSON")
    p_merge.set_defaults(func=cmd_cog_merge)
