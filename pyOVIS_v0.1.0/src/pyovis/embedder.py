from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from .config import DEFAULT_CANDIDATE_INSTRUCTION, DEFAULT_MODEL, DEFAULT_QUERY_INSTRUCTION
from .schemas import SemanticObject


def _l2(vec: np.ndarray) -> np.ndarray:
    vec = np.asarray(vec, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:
        raise ValueError("Embedding norm is zero")
    return vec / norm


class Embedder(ABC):
    backend_name: str
    model_name: str
    dimension: int

    @abstractmethod
    def embed_object(self, obj: SemanticObject) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def embed_text(self, text: str, *, is_query: bool = True) -> np.ndarray:
        raise NotImplementedError


class HashEmbedder(Embedder):
    """Deterministic offline backend for tests and plumbing demos only."""

    backend_name = "hash"
    model_name = "pyovis-hash-test-backend"

    def __init__(self, dim: int = 128):
        self.dimension = int(dim)

    def _encode(self, payload: bytes) -> np.ndarray:
        # Expand SHA-256 blocks deterministically into signed float components.
        chunks = []
        counter = 0
        while len(chunks) * 32 < self.dimension:
            chunks.append(hashlib.sha256(counter.to_bytes(4, "big") + payload).digest())
            counter += 1
        raw = b"".join(chunks)[: self.dimension]
        vec = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 127.5
        return _l2(vec)

    def embed_object(self, obj: SemanticObject) -> np.ndarray:
        payload = (obj.text or obj.uri).encode("utf-8", errors="replace")
        return self._encode(payload)

    def embed_text(self, text: str, *, is_query: bool = True) -> np.ndarray:
        return self._encode(text.encode("utf-8", errors="replace"))


class OvisOmniEmbedder(Embedder):
    """Lazy Ovis-Omni adapter. Heavy dependencies are imported only when selected."""

    backend_name = "ovis"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        query_instruction: str = DEFAULT_QUERY_INSTRUCTION,
        candidate_instruction: str = DEFAULT_CANDIDATE_INSTRUCTION,
    ):
        try:
            import torch
            import torch.nn.functional as F
            from qwen_omni_utils import process_mm_info
            from transformers import AutoModelForMultimodalLM, AutoProcessor
        except ImportError as exc:
            raise RuntimeError(
                "Ovis backend requires optional dependencies. Install: pip install -e '.[ovis]'"
            ) from exc

        self._torch = torch
        self._F = F
        self._process_mm_info = process_mm_info
        self.model_name = model_name
        self.query_instruction = query_instruction
        self.candidate_instruction = candidate_instruction
        self.dimension = 2048

        self.processor = AutoProcessor.from_pretrained(model_name)
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        self.model = AutoModelForMultimodalLM.from_pretrained(
            model_name, torch_dtype=dtype, device_map="auto"
        )
        self.model.eval()

    def _content(self, obj: SemanticObject) -> list[dict]:
        uri = Path(obj.uri).resolve().as_uri()
        if obj.modality in {"text", "pdf_page"}:
            return [{"type": "text", "text": obj.text or ""}]
        if obj.modality == "image":
            return [{"type": "image", "image": uri}]
        if obj.modality == "audio":
            return [{"type": "audio", "audio": uri}]
        if obj.modality == "video":
            return [{"type": "video", "video": uri}]
        raise ValueError(f"Unsupported modality: {obj.modality}")

    def _embed_messages(self, content: list[dict], instruction: str) -> np.ndarray:
        torch = self._torch
        content = list(content) + [{"type": "text", "text": instruction}]
        messages = [{"role": "user", "content": content}]
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        audios, images, videos = self._process_mm_info(messages, use_audio_in_video=True)
        inputs = self.processor(
            text=text,
            audio=audios,
            images=images,
            videos=videos,
            padding=True,
            return_tensors="pt",
            use_audio_in_video=True,
        )
        device = next(self.model.parameters()).device
        inputs = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in inputs.items()}
        with torch.inference_mode():
            outputs = self.model(**inputs, output_hidden_states=True, return_dict=True)
        hidden = getattr(outputs, "last_hidden_state", None)
        if hidden is None:
            hidden = outputs.hidden_states[-1]
        mask = inputs["attention_mask"]
        last = mask.sum(dim=1) - 1
        batch = torch.arange(hidden.shape[0], device=hidden.device)
        embedding = hidden[batch, last]
        embedding = self._F.normalize(embedding.float(), p=2, dim=-1)
        return embedding[0].detach().cpu().numpy().astype(np.float32)

    def embed_object(self, obj: SemanticObject) -> np.ndarray:
        return self._embed_messages(self._content(obj), self.candidate_instruction)

    def embed_text(self, text: str, *, is_query: bool = True) -> np.ndarray:
        instruction = self.query_instruction if is_query else self.candidate_instruction
        return self._embed_messages([{"type": "text", "text": text}], instruction)


def make_embedder(backend: str, model: str = DEFAULT_MODEL) -> Embedder:
    backend = backend.lower()
    if backend == "hash":
        return HashEmbedder()
    if backend == "ovis":
        return OvisOmniEmbedder(model_name=model)
    raise ValueError(f"Unknown backend: {backend}")
