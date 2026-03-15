"""COG Adapter data models — COG bundle types and DeepSigma mapping types.

All models use dataclasses with to_dict/from_dict for serialisation,
following the repo-wide pattern (snake_case internal, camelCase JSON).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── COG-side models ────────────────────────────────────────────────


@dataclass
class CogManifest:
    """Bundle manifest — identity, version, and artifact index."""

    bundle_id: str
    version: str = "1.0"
    created_at: str = ""
    description: str = ""
    artifact_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "bundleId": self.bundle_id,
            "version": self.version,
        }
        if self.created_at:
            d["createdAt"] = self.created_at
        if self.description:
            d["description"] = self.description
        if self.artifact_refs:
            d["artifactRefs"] = self.artifact_refs
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CogManifest:
        return cls(
            bundle_id=data.get("bundleId", data.get("bundle_id", "")),
            version=data.get("version", "1.0"),
            created_at=data.get("createdAt", data.get("created_at", "")),
            description=data.get("description", ""),
            artifact_refs=data.get("artifactRefs", data.get("artifact_refs", [])),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CogProof:
    """Proof metadata — hash chain, signatures, rule seals, timestamps."""

    proof_chain: List[Dict[str, Any]] = field(default_factory=list)
    signatures: List[Dict[str, Any]] = field(default_factory=list)
    rule_seal: Optional[str] = None
    timestamps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.proof_chain:
            d["proofChain"] = self.proof_chain
        if self.signatures:
            d["signatures"] = self.signatures
        if self.rule_seal is not None:
            d["ruleSeal"] = self.rule_seal
        if self.timestamps:
            d["timestamps"] = self.timestamps
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CogProof:
        return cls(
            proof_chain=data.get("proofChain", data.get("proof_chain", [])),
            signatures=data.get("signatures", []),
            rule_seal=data.get("ruleSeal", data.get("rule_seal")),
            timestamps=data.get("timestamps", []),
        )


@dataclass
class CogReplayStep:
    """A single step in a replay sequence."""

    step_index: int
    action: str
    input_ref: str = ""
    output_ref: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "stepIndex": self.step_index,
            "action": self.action,
        }
        if self.input_ref:
            d["inputRef"] = self.input_ref
        if self.output_ref:
            d["outputRef"] = self.output_ref
        if self.timestamp:
            d["timestamp"] = self.timestamp
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CogReplayStep:
        return cls(
            step_index=data.get("stepIndex", data.get("step_index", 0)),
            action=data.get("action", ""),
            input_ref=data.get("inputRef", data.get("input_ref", "")),
            output_ref=data.get("outputRef", data.get("output_ref", "")),
            timestamp=data.get("timestamp", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CogArtifactRef:
    """Reference to a single artifact within a COG bundle."""

    ref_id: str
    ref_type: str  # evidence | rationale | memory | drift | patch
    content_hash: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "refId": self.ref_id,
            "refType": self.ref_type,
        }
        if self.content_hash:
            d["contentHash"] = self.content_hash
        if self.payload:
            d["payload"] = self.payload
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CogArtifactRef:
        return cls(
            ref_id=data.get("refId", data.get("ref_id", "")),
            ref_type=data.get("refType", data.get("ref_type", "")),
            content_hash=data.get("contentHash", data.get("content_hash", "")),
            payload=data.get("payload", {}),
        )


@dataclass
class CogBundle:
    """Top-level COG bundle — manifest, artifacts, proof, and replay."""

    manifest: CogManifest
    artifacts: List[CogArtifactRef] = field(default_factory=list)
    proof: Optional[CogProof] = None
    replay_steps: List[CogReplayStep] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "manifest": self.manifest.to_dict(),
        }
        if self.artifacts:
            d["artifacts"] = [a.to_dict() for a in self.artifacts]
        if self.proof is not None:
            d["proof"] = self.proof.to_dict()
        if self.replay_steps:
            d["replaySteps"] = [s.to_dict() for s in self.replay_steps]
        if self.raw_metadata:
            d["rawMetadata"] = self.raw_metadata
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CogBundle:
        manifest_data = data.get("manifest", {})
        proof_data = data.get("proof")
        return cls(
            manifest=CogManifest.from_dict(manifest_data),
            artifacts=[
                CogArtifactRef.from_dict(a)
                for a in data.get("artifacts", [])
            ],
            proof=CogProof.from_dict(proof_data) if proof_data else None,
            replay_steps=[
                CogReplayStep.from_dict(s)
                for s in data.get("replaySteps", data.get("replay_steps", []))
            ],
            raw_metadata=data.get("rawMetadata", data.get("raw_metadata", {})),
        )


# ── Heuristic suggestion model ────────────────────────────────────


@dataclass
class CogMappingSuggestion:
    """Heuristic suggestion for mapping an unmapped refType to a CERPA stage."""

    original_ref_type: str
    suggested_ref_type: str = ""
    suggested_cerpa_stage: str = ""
    confidence: float = 0.0
    signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "originalRefType": self.original_ref_type,
            "suggestedRefType": self.suggested_ref_type,
            "suggestedCerpaStage": self.suggested_cerpa_stage,
            "confidence": self.confidence,
            "signals": self.signals,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CogMappingSuggestion:
        return cls(
            original_ref_type=data.get("originalRefType", data.get("original_ref_type", "")),
            suggested_ref_type=data.get("suggestedRefType", data.get("suggested_ref_type", "")),
            suggested_cerpa_stage=data.get("suggestedCerpaStage", data.get("suggested_cerpa_stage", "")),
            confidence=data.get("confidence", 0.0),
            signals=data.get("signals", []),
        )


# ── DeepSigma mapping models ──────────────────────────────────────


@dataclass
class DeepSigmaReceipt:
    """Proof receipt for a sealed DeepSigma artifact."""

    artifact_id: str
    seal_hash: str = ""
    sealed_at: str = ""
    proof_metadata: Dict[str, Any] = field(default_factory=dict)
    source_bundle_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "artifactId": self.artifact_id,
        }
        if self.seal_hash:
            d["sealHash"] = self.seal_hash
        if self.sealed_at:
            d["sealedAt"] = self.sealed_at
        if self.proof_metadata:
            d["proofMetadata"] = self.proof_metadata
        if self.source_bundle_id is not None:
            d["sourceBundleId"] = self.source_bundle_id
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeepSigmaReceipt:
        return cls(
            artifact_id=data.get("artifactId", data.get("artifact_id", "")),
            seal_hash=data.get("sealHash", data.get("seal_hash", "")),
            sealed_at=data.get("sealedAt", data.get("sealed_at", "")),
            proof_metadata=data.get("proofMetadata", data.get("proof_metadata", {})),
            source_bundle_id=data.get("sourceBundleId", data.get("source_bundle_id")),
        )


@dataclass
class DeepSigmaReplayRecord:
    """Replay record mapping COG replay steps to DeepSigma lineage."""

    record_id: str
    artifact_id: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    lineage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "recordId": self.record_id,
        }
        if self.artifact_id:
            d["artifactId"] = self.artifact_id
        if self.steps:
            d["steps"] = self.steps
        if self.lineage:
            d["lineage"] = self.lineage
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeepSigmaReplayRecord:
        return cls(
            record_id=data.get("recordId", data.get("record_id", "")),
            artifact_id=data.get("artifactId", data.get("artifact_id", "")),
            steps=data.get("steps", []),
            lineage=data.get("lineage", {}),
        )


@dataclass
class DeepSigmaDecisionArtifact:
    """DeepSigma decision artifact with five-primitive field mapping.

    Wraps the semantic content of a decision with explicit fields for
    each DeepSigma primitive: Truth, Reasoning, Memory, Drift, Patch.
    """

    artifact_id: str
    truth_claims: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: Dict[str, Any] = field(default_factory=dict)
    memory_refs: List[Dict[str, Any]] = field(default_factory=list)
    drift_annotations: List[Dict[str, Any]] = field(default_factory=list)
    patch_refs: List[Dict[str, Any]] = field(default_factory=list)
    receipt: Optional[DeepSigmaReceipt] = None
    replay: Optional[DeepSigmaReplayRecord] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "artifactId": self.artifact_id,
        }
        if self.truth_claims:
            d["truthClaims"] = self.truth_claims
        if self.reasoning:
            d["reasoning"] = self.reasoning
        if self.memory_refs:
            d["memoryRefs"] = self.memory_refs
        if self.drift_annotations:
            d["driftAnnotations"] = self.drift_annotations
        if self.patch_refs:
            d["patchRefs"] = self.patch_refs
        if self.receipt is not None:
            d["receipt"] = self.receipt.to_dict()
        if self.replay is not None:
            d["replay"] = self.replay.to_dict()
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeepSigmaDecisionArtifact:
        receipt_data = data.get("receipt")
        replay_data = data.get("replay")
        return cls(
            artifact_id=data.get("artifactId", data.get("artifact_id", "")),
            truth_claims=data.get("truthClaims", data.get("truth_claims", [])),
            reasoning=data.get("reasoning", {}),
            memory_refs=data.get("memoryRefs", data.get("memory_refs", [])),
            drift_annotations=data.get("driftAnnotations", data.get("drift_annotations", [])),
            patch_refs=data.get("patchRefs", data.get("patch_refs", [])),
            receipt=DeepSigmaReceipt.from_dict(receipt_data) if receipt_data else None,
            replay=DeepSigmaReplayRecord.from_dict(replay_data) if replay_data else None,
            metadata=data.get("metadata", {}),
        )
