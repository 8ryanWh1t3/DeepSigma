"""COG bundle replay extraction — convert replay semantics to DeepSigma.

Functions:
    extract_replay_sequence    — sorted list of CogReplaySteps
    to_deepsigma_replay_record — convert to DeepSigmaReplayRecord
"""

from __future__ import annotations

from typing import List

from .models import CogBundle, CogReplayStep, DeepSigmaReplayRecord


def extract_replay_sequence(bundle: CogBundle) -> List[CogReplayStep]:
    """Return replay steps from a CogBundle, sorted by step_index.

    Returns an empty list if the bundle has no replay data.
    """
    if not bundle.replay_steps:
        return []
    return sorted(bundle.replay_steps, key=lambda s: s.step_index)


def to_deepsigma_replay_record(bundle: CogBundle) -> DeepSigmaReplayRecord:
    """Convert a CogBundle's replay data into a DeepSigmaReplayRecord.

    Maps COG replay steps to DeepSigma-compatible step dicts,
    preserving original metadata.
    """
    steps = extract_replay_sequence(bundle)

    ds_steps = []
    for step in steps:
        ds_step = {
            "action": step.action,
            "stepIndex": step.step_index,
        }
        if step.input_ref:
            ds_step["inputRef"] = step.input_ref
        if step.output_ref:
            ds_step["outputRef"] = step.output_ref
        if step.timestamp:
            ds_step["timestamp"] = step.timestamp
        if step.metadata:
            ds_step["metadata"] = step.metadata
        ds_steps.append(ds_step)

    return DeepSigmaReplayRecord(
        record_id=f"replay-{bundle.manifest.bundle_id}",
        artifact_id=bundle.manifest.bundle_id,
        steps=ds_steps,
        lineage={
            "sourceBundleId": bundle.manifest.bundle_id,
            "sourceVersion": bundle.manifest.version,
            "stepCount": len(ds_steps),
        },
    )
