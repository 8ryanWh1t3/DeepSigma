# pyOVIS Σ

**pyOVIS** is the Deep Sigma multimodal semantic discovery layer built around Ovis omni-modal embeddings.

It accepts **text, PDF, image, audio, and video**, produces normalized embeddings, stores them in a local SQLite semantic index, performs cross-modal similarity search, detects semantic residuals, and exports **RESONATOR-ready candidate edges**.

> **pyOVIS discovers. RESONATOR interprets. PATHFINDER structures. CERPA governs.**

## Core invariant

pyOVIS never declares enterprise truth. Every discovered relationship is emitted as:

```json
{
  "relationship": "UNRESOLVED",
  "authoritative": false,
  "requires_resonator": true
}
```

## Architecture

```text
RAW REALITY
   │
   ├── text / .txt / .md
   ├── PDF → page-level text objects
   ├── images
   ├── audio
   └── video
        ↓
      pyOVIS
        ↓
  OVIS EMBEDDINGS
        ↓
  SQLITE SEMANTIC MEMORY
        ↓
  NEIGHBORS / RESIDUALS
        ↓
  CANDIDATE EDGES
        ↓
     RESONATOR
        ↓
     PATHFINDER
        ↓
       CERPA
```

## Model basis

The default production backend targets `ATH-MaaS/Ovis-Omni-Embedding-3B`. The model maps text, image, video, audio, and interleaved inputs into one representation space. Its documented retrieval path is: task instruction + native chat template → independent query/candidate encoding → final-layer hidden state at the last non-padding token → L2 normalization → cosine similarity.

pyOVIS does **not** bundle model weights. Install the optional Ovis dependencies and the model is downloaded through Hugging Face at runtime.

## Install

Core package and deterministic development backend:

```bash
pip install -e .
```

With Ovis support:

```bash
pip install -e ".[ovis]"
```

Development:

```bash
pip install -e ".[dev]"
pytest
```

## Five-minute demo without a GPU

The `hash` backend is deterministic and intended only for tests/demo plumbing. It does **not** provide semantic quality comparable to Ovis.

```bash
pyovis init demo.db
pyovis ingest demo.db examples/corpus --backend hash
pyovis search demo.db "small unmanned aircraft near a restricted perimeter" --backend hash
pyovis stats demo.db
```

## Production Ovis usage

```bash
pyovis init mission.db

pyovis ingest mission.db ./mission-corpus \
  --backend ovis \
  --model ATH-MaaS/Ovis-Omni-Embedding-3B

pyovis search mission.db \
  "small unmanned aircraft approaching a restricted installation boundary" \
  --backend ovis \
  --top-k 10
```

Supported file classes in v0.1.0:

- Text: `.txt`, `.md`, `.json`, `.jsonl`, `.csv`, `.log`
- PDF: page-level extracted text with page provenance
- Image: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`
- Audio: `.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg`
- Video: `.mp4`, `.mov`, `.mkv`, `.webm`, `.avi`

## Neighbor search

```bash
pyovis neighbors mission.db <OBJECT_ID> --top-k 10
```

## Semantic residuals

A semantic residual is an object whose closest known neighbor is below a chosen similarity threshold. It is a **discovery signal**, not a claim that the object is novel or important.

```bash
pyovis residuals mission.db --threshold 0.45
```

## RESONATOR export

```bash
pyovis export-resonator mission.db candidates.json \
  --threshold 0.70 \
  --top-k 5
```

Example record:

```json
{
  "type": "SemanticCandidateEdge",
  "source": "OBJ-...",
  "candidate": "OBJ-...",
  "similarity": 0.913247,
  "relationship": "UNRESOLVED",
  "authoritative": false,
  "requires_resonator": true,
  "discovered_by": "pyOVIS",
  "discovery_method": "OVIS_OMNI_EMBEDDING_COSINE"
}
```

## Provenance

Every ingested object stores:

- object ID
- source URI/path
- modality
- SHA-256 of the source file
- source size and modification time
- PDF page when applicable
- embedding model/backend
- embedding dimension
- creation timestamp
- user metadata

The vector store is **semantic memory, not authority**.

## Python API

```python
from pathlib import Path
from pyovis.embedder import HashEmbedder
from pyovis.ingest import Ingestor
from pyovis.store import SemanticStore

store = SemanticStore("demo.db")
store.initialize()
embedder = HashEmbedder(dim=128)
Ingestor(store, embedder).ingest_path(Path("examples/corpus"))

hits = store.search(embedder.embed_text("restricted perimeter"), top_k=5)
for hit in hits:
    print(hit.object_id, hit.score)
```

## Design boundaries

pyOVIS v0.1.0 deliberately does **not**:

- create authoritative RDF/SKOS relationships
- change ontology state
- mutate CERPA state
- infer legal/policy authority
- replace RESONATOR
- use embedding similarity as proof

Similarity is evidence for **where to look next**, not a declaration of truth.

## Repository contents

```text
src/pyovis/            installable package
tests/                  unit tests (no model download required)
examples/               small safe demo corpus
docs/                   architecture + integration contract
.github/workflows/       CI + package build
```

## Upstream model attribution

Ovis-Omni-Embedding is developed by the Alibaba ATH-MaaS team and released under Apache-2.0. pyOVIS is an independent Deep Sigma integration layer and is not an official Ovis project. See `NOTICE` and `docs/model-basis.md`.

## License

Apache License 2.0. See `LICENSE`.

## Upstream references

- Ovis-Omni-Embedding repository: https://github.com/ATH-MaaS/Ovis-Omni-Embedding
- Ovis-Omni-Embedding-3B model: https://huggingface.co/ATH-MaaS/Ovis-Omni-Embedding-3B
- Technical report: https://arxiv.org/abs/2609.25165
- Qwen Omni preprocessing utilities: https://github.com/QwenLM/Qwen2.5-Omni/tree/main/qwen-omni-utils
