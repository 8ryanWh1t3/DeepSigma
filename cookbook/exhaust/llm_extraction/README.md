# LLM Extraction — Anthropic-Backed Refiner

Enable `claude-haiku-4-5-20251001` to extract higher-quality TRUTH /
REASONING / MEMORY buckets from your episodes instead of the rule-based
default.

**Time:** ~30 seconds per episode (network round-trip to Anthropic)
**Requires:** `ANTHROPIC_API_KEY` + `pip install -e ".[exhaust-llm]"`

---

## Setup

```bash
pip install -e ".[exhaust-llm]"
export ANTHROPIC_API_KEY="sk-ant-..."
export EXHAUST_USE_LLM="1"
```

Verify the package is available:

```bash
python -c "import anthropic; print(anthropic.__version__)"
```

---

## Run the demo script

```bash
python cookbook/exhaust/llm_extraction/demo.py
```

Expected output:

```
=== Exhaust LLM Extraction Demo ===
Episode: ep-demo-001  (5 events)

Refining with LLM extraction...

--- Results ---
Grade:           B
Coherence score: 76.5
Truth items:     2
  [0.92] Service-alpha is healthy, running version 2.4.1
  [0.85] Latency is 1240ms
Reasoning items: 1
  [0.80] I recommend monitoring for another 30 minutes before rollback
Memory items:    3
  service-alpha (service)
  check_deployment (tool)
  ep-demo-001 (episode)

=== Done ===
```

---

## Verify via API

```bash
EP_ID="ep-demo-001"
curl -s -X POST "http://localhost:8000/api/exhaust/episodes/$EP_ID/refine" \
  | jq '{grade, coherence_score, truth_count: (.truth | length)}'
```

---

## Fallback behaviour

If `ANTHROPIC_API_KEY` is unset or the API call fails, the rule-based
extractor runs automatically. No error is raised and no episode is lost.

To confirm LLM extraction ran vs. fell back, check the episode grade:
- LLM extraction → typically **B** or **A** for well-structured episodes
- Rule-based → typically **C** or **D**

---

## Configuration

Change the model in code:

```python
from engine.exhaust_llm_extractor import LLMExtractor
extractor = LLMExtractor(model="claude-sonnet-4-5-20250929", max_tokens=4096)
buckets = extractor.extract(episode)
```

Or set `EXHAUST_USE_LLM=0` to revert to rule-based at any time without
redeploying.
