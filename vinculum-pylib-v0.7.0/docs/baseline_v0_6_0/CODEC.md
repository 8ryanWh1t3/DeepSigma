# Codec preservation audit

An LLM or another transformation may preserve a number while changing what the number refers to. VINCULUM evaluates the declared representations before and after that transformation; it does not require or run the LLM.

## Synthetic demonstration

Source: “No tracks were detected in the defined 30-second window. Sensor coverage was 60%.”

Generated summary: “The entire sector was observed, and no aircraft were present.”

The fixture explicitly resolves these into typed representations rather than claiming unrestricted NLP extraction:

- Zero detections -> a count of detections.
- Entire sector observed -> observed coverage of 100%.
- No aircraft present -> a count of physical presence.
- Recorded coverage -> 60% over the same declared sector and interval.

Evaluation:

- 0 detected versus 0 detected: aligned.
- 100% observed versus 60% observed: numeric conflict; delta is -40 percentage points.
- 0 present versus 0 detected: different concepts, NOT_COMPARABLE. No detection model has been supplied to justify the inference from detection to physical absence.

The codec layer reports that a concept bridge is unsupported rather than treating zero as proof that nothing existed.

## Preservation checks

`Transformation` names material source nodes and target nodes. `CodecEvaluator` consumes a report bound to that exact graph snapshot. It checks pairs between the declared endpoints and identifies:

- NUMERIC_CONTENT_PRESERVED
- VALUE_CHANGED
- SCOPE_OR_MEANING_CHANGED
- UNCERTAINTY_NARROWED
- PRECISION_LOST
- SUPPORT_ANNOTATION_OMITTED
- SUPPORT_INCREASE_REQUIRES_EVIDENCE
- MATERIAL_SOURCE_UNPAIRED
- TARGET_ADDITION_UNSUPPORTED
- PRESERVATION_UNRESOLVED

A source interval [0,1] reproduced as [0,1] is faithful even if underlying support is weak. A target point 0 derived from [0,1] narrows uncertainty and requires additional evidence. A support score cannot become stronger merely because a summary sounds more confident.

## Honest limits

The material inventory is declared by the caller or extractor. Coverage is over that inventory, not all semantics in arbitrary documents. Omissions outside the declared inventory cannot be detected. A detected change may be intentional and justified by new evidence; the audit flags it for explanation, not moral or factual judgment.

No probability of textual truth, universal semantic equivalence, causal proof or operational clearance is produced.
