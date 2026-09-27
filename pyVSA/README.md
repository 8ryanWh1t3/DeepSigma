# Deep Sigma VSA — Voice Semantic Adapter

**Version:** 0.1.0

Deep Sigma VSA converts human speech or transcripts into **candidate, governed semantic objects** that downstream Deep Sigma systems can inspect, connect, challenge, and govern.

> **Audio → Words → Meaning → Governed Semantic Objects**

VSA is an **ingestion capability**, not a new Deep Sigma product. It sits upstream of RESONATOR, PATHFINDER, DOC COMPOSER, CERPA, Coherence Ops, and Institutional Memory.

## Design rules

1. **Preserve the source.** Every semantic object points back to evidence and provenance.
2. **Never silently invent authority.** Voice-derived objects are `CANDIDATE` by default.
3. **Separate transcription from interpretation.** ASR and semantic extraction are pluggable stages.
4. **Expose uncertainty.** Confidence, modality, negation, and assumptions remain explicit.
5. **Graph-ready by construction.** Outputs can project to RDF-style triples, JSON-LD-like records, PATHFINDER edges, and CERPA candidate claims.
6. **Offline first.** The core package has no cloud dependency.

## Architecture

```text
Audio / Transcript
      ↓
ASR Adapter (optional)
      ↓
Transcript + speaker/timestamp provenance
      ↓
Semantic Extractor
      ↓
Claim / Entity / Event / Relationship / Evidence / Intent / Assumption
      ↓
Governance Envelope
      ↓
SemanticPacket
      ├── RESONATOR payload
      ├── PATHFINDER graph
      ├── DOC COMPOSER candidate clauses
      ├── CERPA candidate claims
      └── RDF / JSON-LD-friendly serialization
```

## Quick start

```python
from deep_sigma_vsa import VoiceSemanticAdapter

vsa = VoiceSemanticAdapter()
packet = vsa.from_transcript(
    "We can probably cover the eastern sector with the current systems, "
    "but I'm concerned about the gap near the river.",
    speaker_id="commander-01",
)

print(packet.to_json(indent=2))
print(packet.to_resonator_payload())
print(packet.to_pathfinder_payload())
```

The default extractor is intentionally conservative. It creates source-linked candidate meaning without pretending to perform full open-domain understanding. Replace it with a stronger local or enterprise NLP/LLM adapter when needed.

## Audio ingestion

The core library defines an `ASRAdapter` protocol but does not force Whisper, cloud APIs, or any specific model. Supply an adapter:

```python
class MyASR:
    def transcribe(self, source):
        ...

vsa = VoiceSemanticAdapter(asr=MyASR())
packet = vsa.from_audio("briefing.wav")
```

## Authority boundary

VSA does **not** declare spoken statements authoritative. The default status is:

```text
CANDIDATE
```

Promotion to authoritative state belongs downstream under the appropriate Deep Sigma governance path (for example, CERPA / human authority / DOC COMPOSER controls).

## Development

```bash
python -m pip install -e .[dev]
pytest -q
```

## Package map

- `models.py` — canonical semantic objects
- `pipeline.py` — VSA orchestration
- `adapters/base.py` — adapter protocols
- `adapters/offline.py` — conservative offline semantic extractor
- `graph.py` — RDF-style triples and system projections
- `serialization.py` — stable JSON helpers
- `cli.py` — transcript CLI

