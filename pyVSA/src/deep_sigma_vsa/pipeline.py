from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from .adapters.base import ASRAdapter, AudioSource, PacketPostProcessor, SemanticExtractor
from .adapters.offline import ConservativeSemanticExtractor
from .models import Confidence, SemanticPacket, Transcript, TranscriptSegment


class VoiceSemanticAdapter:
    """Deep Sigma VSA orchestration surface."""

    def __init__(
        self,
        *,
        asr: ASRAdapter | None = None,
        extractor: SemanticExtractor | None = None,
        postprocessors: tuple[PacketPostProcessor, ...] = (),
    ) -> None:
        self.asr = asr
        self.extractor = extractor or ConservativeSemanticExtractor()
        self.postprocessors = postprocessors

    def from_transcript(
        self,
        text: str,
        *,
        source_id: str | None = None,
        speaker_id: str | None = None,
        language: str = "en",
        confidence: float = 1.0,
    ) -> SemanticPacket:
        if not text.strip():
            raise ValueError("transcript text cannot be empty")
        source_id = source_id or f"transcript-{uuid4().hex[:12]}"
        transcript = Transcript(
            text=text,
            source_id=source_id,
            language=language,
            segments=(
                TranscriptSegment(
                    text=text,
                    speaker_id=speaker_id,
                    confidence=Confidence(confidence, "caller-supplied transcript confidence"),
                ),
            ),
        )
        return self._run(transcript)

    def from_segments(
        self,
        segments: list[TranscriptSegment],
        *,
        source_id: str | None = None,
        language: str = "en",
    ) -> SemanticPacket:
        if not segments:
            raise ValueError("segments cannot be empty")
        source_id = source_id or f"transcript-{uuid4().hex[:12]}"
        transcript = Transcript(
            text=" ".join(s.text for s in segments),
            source_id=source_id,
            language=language,
            segments=tuple(segments),
        )
        return self._run(transcript)

    def from_audio(self, path: str | Path, *, language: str = "en") -> SemanticPacket:
        if self.asr is None:
            raise RuntimeError(
                "No ASR adapter configured. Supply an ASRAdapter or use from_transcript()."
            )
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        source_id = self._audio_source_id(path)
        transcript = self.asr.transcribe(AudioSource(path=path, source_id=source_id, language=language))
        return self._run(transcript)

    def _run(self, transcript: Transcript) -> SemanticPacket:
        packet = self.extractor.extract(transcript)
        for processor in self.postprocessors:
            packet = processor.process(packet)
        return packet

    @staticmethod
    def _audio_source_id(path: Path) -> str:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        return f"audio-sha256-{digest}"
