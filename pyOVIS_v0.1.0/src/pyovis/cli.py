from __future__ import annotations

import json
from pathlib import Path

import typer

from .config import DEFAULT_MODEL
from .embedder import make_embedder
from .ingest import Ingestor
from .resonator import export_candidate_edges
from .search import find_residuals
from .store import SemanticStore

app = typer.Typer(help="pyOVIS — Deep Sigma multimodal semantic discovery")


def _store(db: Path) -> SemanticStore:
    store = SemanticStore(db)
    store.initialize()
    return store


def _print_rows(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(value))
    typer.echo("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    typer.echo("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        typer.echo("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))


@app.command()
def init(db: Path):
    """Initialize a local SQLite semantic store."""
    _store(db)
    typer.echo(f"Initialized {db}")


@app.command()
def ingest(
    db: Path,
    path: Path,
    backend: str = typer.Option("hash", help="hash (demo/test) or ovis"),
    model: str = typer.Option(DEFAULT_MODEL),
):
    """Ingest a file or directory."""
    store = _store(db)
    embedder = make_embedder(backend, model=model)
    result = Ingestor(store, embedder).ingest_path(path)
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command()
def search(
    db: Path,
    query: str,
    backend: str = typer.Option("hash"),
    model: str = typer.Option(DEFAULT_MODEL),
    top_k: int = typer.Option(10, min=1),
):
    """Search the semantic store with a text query."""
    store = _store(db)
    embedder = make_embedder(backend, model=model)
    hits = store.search(embedder.embed_text(query, is_query=True), top_k=top_k)
    rows = [[f"{h.score:.4f}", h.object_id, h.modality, h.uri] for h in hits]
    _print_rows(["score", "object", "modality", "source"], rows)


@app.command()
def neighbors(db: Path, object_id: str, top_k: int = typer.Option(10, min=1)):
    """Find nearest neighbors of an already indexed object."""
    store = _store(db)
    vec = store.get_vector(object_id)
    if vec is None:
        raise typer.BadParameter(f"Object not found: {object_id}")
    hits = store.search(vec, top_k=top_k, exclude_id=object_id)
    rows = [[f"{h.score:.4f}", h.object_id, h.modality, h.uri] for h in hits]
    _print_rows(["score", "object", "modality", "source"], rows)


@app.command()
def residuals(db: Path, threshold: float = typer.Option(0.45)):
    """List semantic residuals below a nearest-neighbor threshold."""
    store = _store(db)
    found = find_residuals(store, threshold=threshold)
    rows = [[r.object_id, r.nearest_id or "—", "—" if r.nearest_score is None else f"{r.nearest_score:.4f}"] for r in found]
    _print_rows(["object", "nearest", "score"], rows)


@app.command("export-resonator")
def export_resonator(
    db: Path,
    output: Path,
    threshold: float = typer.Option(0.70),
    top_k: int = typer.Option(5, min=1),
):
    """Export unresolved candidate edges for RESONATOR."""
    store = _store(db)
    count = export_candidate_edges(store, output, threshold=threshold, top_k=top_k)
    typer.echo(f"Exported {count} candidate edges -> {output}")


@app.command()
def stats(db: Path):
    """Show store statistics."""
    store = _store(db)
    typer.echo(json.dumps(store.stats(), indent=2, sort_keys=True))


@app.command()
def doctor():
    """Check optional runtime dependencies without downloading the model."""
    checks = {}
    for name in ("torch", "transformers", "qwen_omni_utils"):
        try:
            __import__(name)
            checks[name] = "available"
        except Exception:
            checks[name] = "missing"
    checks["default_model"] = DEFAULT_MODEL
    typer.echo(json.dumps(checks, indent=2, sort_keys=True))


if __name__ == "__main__":
    app()
