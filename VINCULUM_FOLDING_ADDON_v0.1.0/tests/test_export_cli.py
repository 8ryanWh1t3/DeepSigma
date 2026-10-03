import hashlib
import json
from pathlib import Path
import pytest
from vinculum_folding import FoldError, export_bundle, verify_bundle
from vinculum_folding.cli import main


def test_export_roundtrip(episode, tmp_path):
    out = export_bundle(episode, tmp_path / "bundle")
    assert verify_bundle(out) == episode
    assert json.loads((out / "review_input.json").read_text())["automatic_actions"] == 0


def test_exports_do_not_overwrite(episode, tmp_path):
    out = export_bundle(episode, tmp_path / "bundle")
    old = (out / "episode.json").read_bytes()
    with pytest.raises(FileExistsError): export_bundle(episode, out)
    assert (out / "episode.json").read_bytes() == old


@pytest.mark.parametrize("filename", ["episode.json", "view.json", "audit.json", "review_input.json", "READ_ME.md"])
def test_tampered_bundle_detected(episode, tmp_path, filename):
    out = export_bundle(episode, tmp_path / "bundle")
    with (out / filename).open("a") as f: f.write(" ")
    with pytest.raises(FoldError): verify_bundle(out)


def test_recomputed_manifest_does_not_hide_projection_change(episode, tmp_path):
    out = export_bundle(episode, tmp_path / "bundle")
    view = json.loads((out / "view.json").read_text()); view["read_only"] = False
    raw = json.dumps(view).encode(); (out / "view.json").write_bytes(raw)
    manifest = json.loads((out / "manifest.json").read_text())
    manifest["files"]["view.json"] = hashlib.sha256(raw).hexdigest()
    (out / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(FoldError): verify_bundle(out)


def test_manifest_path_injection_refused(episode, tmp_path):
    out = export_bundle(episode, tmp_path / "bundle")
    manifest = json.loads((out / "manifest.json").read_text())
    manifest["files"]["../outside"] = "a" * 64
    (out / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(FoldError): verify_bundle(out)


def test_unexpected_files_refused(episode, tmp_path):
    out = export_bundle(episode, tmp_path / "bundle")
    (out / "run.py").write_text("raise RuntimeError('must never execute')")
    with pytest.raises(FoldError): verify_bundle(out)


def test_symlink_refused(episode, tmp_path):
    out = export_bundle(episode, tmp_path / "bundle")
    raw = (out / "view.json").read_bytes()
    outside = tmp_path / "outside.json"; outside.write_bytes(raw)
    (out / "view.json").unlink(); (out / "view.json").symlink_to(outside)
    with pytest.raises(FoldError): verify_bundle(out)


def test_cli_demo_inspect_unfold_verify(tmp_path, capsys):
    out = tmp_path / "demo"
    assert main(["demo", "--out", str(out)]) == 0
    assert main(["inspect", str(out / "episode.json")]) == 0
    assert main(["unfold", str(out / "episode.json"), "summary-derivation"]) == 0
    assert main(["verify", str(out)]) == 0
    assert "SCOPE_EXPANSION_REVIEW" in capsys.readouterr().out
    assert main(["demo", "--out", str(out)]) == 2
    assert main(["inspect", str(tmp_path / "absent.json")]) == 2
