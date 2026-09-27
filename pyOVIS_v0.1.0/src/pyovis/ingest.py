from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from .embedder import Embedder
from .provenance import file_provenance
from .schemas import SemanticObject
from .store import SemanticStore

TEXT_EXTS = {".txt", ".md", ".json", ".jsonl", ".csv", ".log"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


def modality_for(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in TEXT_EXTS:
        return "text"
    if ext == ".pdf":
        return "pdf"
    if ext in IMAGE_EXTS:
        return "image"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    return None


def _object_id(sha: str, suffix: str = "") -> str:
    base = f"{sha}:{suffix}" if suffix else sha
    return "OBJ-" + uuid.uuid5(uuid.NAMESPACE_URL, base).hex[:20].upper()


def objects_from_file(path: Path) -> list[SemanticObject]:
    prov = file_provenance(path)
    modality = modality_for(path)
    if modality is None:
        return []
    if modality == "pdf":
        reader = PdfReader(str(path))
        out = []
        for idx, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            out.append(
                SemanticObject(
                    id=_object_id(prov["sha256"], f"page:{idx}"),
                    modality="pdf_page",
                    uri=prov["uri"],
                    sha256=prov["sha256"],
                    size_bytes=prov["size_bytes"],
                    mtime_ns=prov["mtime_ns"],
                    text=text,
                    page=idx,
                    metadata={"filename": path.name},
                )
            )
        return out
    text = None
    if modality == "text":
        text = path.read_text(encoding="utf-8", errors="replace")
    return [
        SemanticObject(
            id=_object_id(prov["sha256"]),
            modality=modality,
            uri=prov["uri"],
            sha256=prov["sha256"],
            size_bytes=prov["size_bytes"],
            mtime_ns=prov["mtime_ns"],
            text=text,
            metadata={"filename": path.name},
        )
    ]


def iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for item in sorted(path.rglob("*")):
        if item.is_file() and modality_for(item) is not None:
            yield item


class Ingestor:
    def __init__(self, store: SemanticStore, embedder: Embedder):
        self.store = store
        self.embedder = embedder

    def ingest_path(self, path: Path) -> dict:
        files = 0
        objects = 0
        skipped = 0
        for file_path in iter_files(path):
            files += 1
            objs = objects_from_file(file_path)
            if not objs:
                skipped += 1
                continue
            for obj in objs:
                vec = self.embedder.embed_object(obj)
                self.store.upsert(obj, vec, self.embedder.backend_name, self.embedder.model_name)
                objects += 1
        return {"files": files, "objects": objects, "skipped": skipped}
