"""Portable sidecar bundles. Rendering of radial graphics remains a host UI concern."""
from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from .engine import audit, project, review_input
from .model import BOUNDARY, FoldEpisode, FoldError, canonical, load_json


def export_bundle(episode: FoldEpisode, directory: str | Path) -> Path:
    """Write a new directory only. No source, host output or existing export is overwritten."""
    out = Path(directory)
    if out.exists():
        raise FileExistsError(f"output already exists: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".fold-", dir=out.parent) as temporary:
        root = Path(temporary)
        payloads = {"episode.json": episode.to_dict(), "view.json": project(episode),
                    "audit.json": audit(episode).to_dict(), "review_input.json": review_input(episode)}
        for name, value in payloads.items():
            (root / name).write_text(canonical(value) + "\n", encoding="utf-8")
        # Markdown is deliberately descriptive; no scores or claimed UI behavior.
        (root / "READ_ME.md").write_text(
            "# VINCULUM — The Navigable Fold\n\n"
            f"Episode `{episode.episode_id}`, revision {episode.revision}.\n\n"
            f"Content digest: `{episode.digest}`\n\n"
            "`episode.json` is the complete retained snapshot. `view.json` is a read-only UI data contract, not a rendered viewer. "
            "`audit.json` holds structural findings. `review_input.json` is a non-executing REVIEW handoff.\n\n"
            + BOUNDARY + "\n", encoding="utf-8")
        manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir())}
        (root / "manifest.json").write_text(canonical({"schema": "vinculum.folding.bundle/1",
            "episode_digest": episode.digest, "files": manifest, "signed": False}) + "\n", encoding="utf-8")
        # Reserve destination atomically. There is no check-then-overwrite rename race.
        out.mkdir(exist_ok=False)
        for path in root.iterdir():
            with (out / path.name).open("xb") as dest:
                dest.write(path.read_bytes())
    return out


def verify_bundle(directory: str | Path) -> FoldEpisode:
    """Verify supplied bundle hashes and reproduced projections, not authenticity."""
    root = Path(directory).resolve()
    if (root / "manifest.json").is_symlink():
        raise FoldError("bundle manifest must not be a symbolic link")
    manifest = load_json(root / "manifest.json")
    expected = {"episode.json", "view.json", "audit.json", "review_input.json", "READ_ME.md"}
    if not isinstance(manifest, dict) or set(manifest) != {"schema", "episode_digest", "files", "signed"} or manifest["schema"] != "vinculum.folding.bundle/1" or manifest["signed"] is not False:
        raise FoldError("invalid bundle manifest")
    if {p.name for p in root.iterdir()} != expected | {"manifest.json"}:
        raise FoldError("bundle contains missing or unexpected files")
    if not isinstance(manifest["files"], dict) or set(manifest["files"]) != expected:
        raise FoldError("bundle file inventory differs from the fixed contract")
    for name, expected_hash in manifest["files"].items():
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise FoldError("bundle source file missing or is a symbolic link")
        # Bounded read even if a manifest was replaced.
        with path.open("rb") as stream:
            raw = stream.read(8_000_001)
        if len(raw) > 8_000_000 or hashlib.sha256(raw).hexdigest() != expected_hash:
            raise FoldError("bundle file hash/size check failed")
    ep = FoldEpisode.load(root / "episode.json")
    if ep.digest != manifest["episode_digest"]:
        raise FoldError("bundle episode digest differs")
    for name, value in (("view.json", project(ep)), ("audit.json", audit(ep).to_dict()),
                        ("review_input.json", review_input(ep))):
        if canonical(load_json(root / name)) != canonical(value):
            raise FoldError("bundle projection does not reproduce from the episode")
    return ep
