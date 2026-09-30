from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .exceptions import GovernanceError, TrustError
from .governance import GovernanceContext
from .receipts import canonical_json, sha256_receipt


class TrustStatus(str, Enum):
    TRUSTED = "TRUSTED"
    UNINITIALIZED = "UNINITIALIZED"
    CHECKPOINT_LOST = "CHECKPOINT_LOST"
    CHECKPOINT_CORRUPT = "CHECKPOINT_CORRUPT"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    DEPLOYMENT_MISMATCH = "DEPLOYMENT_MISMATCH"
    ROOT_KEY_MISMATCH = "ROOT_KEY_MISMATCH"
    CONTEXT_HASH_MISMATCH = "CONTEXT_HASH_MISMATCH"
    ROLLBACK_REJECTED = "ROLLBACK_REJECTED"
    EPOCH_GAP = "EPOCH_GAP"
    CHAIN_MISMATCH = "CHAIN_MISMATCH"
    CHECKPOINT_WRITE_FAILED = "CHECKPOINT_WRITE_FAILED"
    CURRENT_BUNDLE_MISMATCH = "CURRENT_BUNDLE_MISMATCH"


@dataclass(frozen=True)
class RootTrustAnchor:
    """Pinned public-key root used to authenticate governance bundles.

    The root is immutable once the runtime is constructed. VINCULUM intentionally
    provides no runtime `set_root()` method.
    """

    deployment_id: str
    key_id: str
    public_key_b64: str
    algorithm: str = "Ed25519"

    def __post_init__(self) -> None:
        if not self.deployment_id.strip():
            raise TrustError("deployment_id cannot be empty")
        if not self.key_id.strip():
            raise TrustError("root key_id cannot be empty")
        if self.algorithm != "Ed25519":
            raise TrustError(f"unsupported root algorithm: {self.algorithm}")
        try:
            key = base64.b64decode(self.public_key_b64, validate=True)
            Ed25519PublicKey.from_public_bytes(key)
        except Exception as exc:  # pragma: no cover - exact crypto errors vary
            raise TrustError("invalid Ed25519 root public key") from exc

    @classmethod
    def from_public_key(
        cls,
        *,
        deployment_id: str,
        key_id: str,
        public_key: Ed25519PublicKey,
    ) -> "RootTrustAnchor":
        raw = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return cls(
            deployment_id=deployment_id,
            key_id=key_id,
            public_key_b64=base64.b64encode(raw).decode("ascii"),
        )

    def public_key(self) -> Ed25519PublicKey:
        return Ed25519PublicKey.from_public_bytes(base64.b64decode(self.public_key_b64))

    def receipt_view(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "key_id": self.key_id,
            "public_key_b64": self.public_key_b64,
            "algorithm": self.algorithm,
        }

    def sha256(self) -> str:
        return sha256_receipt(self.receipt_view())


@dataclass(frozen=True)
class SignedGovernanceBundle:
    """Root-signed, epoch-ordered materialized governance state."""

    deployment_id: str
    epoch: int
    root_key_id: str
    context: Mapping[str, Any]
    context_sha256: str
    supersedes_hash: str | None
    signature_b64: str
    issued_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema: str = "vinculum.trusted-governance.v0.3"

    def __post_init__(self) -> None:
        if not self.deployment_id.strip():
            raise TrustError("bundle deployment_id cannot be empty")
        if self.epoch < 1:
            raise TrustError("bundle epoch must be >= 1")
        if not self.root_key_id.strip():
            raise TrustError("bundle root_key_id cannot be empty")
        if len(self.context_sha256) != 64:
            raise TrustError("bundle context_sha256 must be a SHA-256 digest")
        if self.supersedes_hash is not None and len(self.supersedes_hash) != 64:
            raise TrustError("bundle supersedes_hash must be a SHA-256 digest")
        try:
            base64.b64decode(self.signature_b64, validate=True)
        except Exception as exc:
            raise TrustError("bundle signature is not valid base64") from exc

    def unsigned_view(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "deployment_id": self.deployment_id,
            "epoch": self.epoch,
            "root_key_id": self.root_key_id,
            "context": dict(self.context),
            "context_sha256": self.context_sha256,
            "supersedes_hash": self.supersedes_hash,
            "issued_at": self.issued_at,
            "metadata": dict(self.metadata),
        }

    def receipt_view(self) -> dict[str, Any]:
        return {**self.unsigned_view(), "signature_b64": self.signature_b64}

    def sha256(self) -> str:
        return sha256_receipt(self.receipt_view())

    def materialize_context(self) -> GovernanceContext:
        ctx = GovernanceContext.from_dict(self.context)
        if ctx.sha256() != self.context_sha256:
            raise TrustError("materialized governance context does not match bundle context_sha256")
        return ctx

    def verify(self, root: RootTrustAnchor) -> TrustStatus:
        if self.deployment_id != root.deployment_id:
            return TrustStatus.DEPLOYMENT_MISMATCH
        if self.root_key_id != root.key_id:
            return TrustStatus.ROOT_KEY_MISMATCH
        try:
            root.public_key().verify(
                base64.b64decode(self.signature_b64),
                canonical_json(self.unsigned_view()).encode("utf-8"),
            )
        except InvalidSignature:
            return TrustStatus.SIGNATURE_INVALID
        except Exception:
            return TrustStatus.SIGNATURE_INVALID
        try:
            context = GovernanceContext.from_dict(self.context)
        except Exception:
            return TrustStatus.CONTEXT_HASH_MISMATCH
        if context.sha256() != self.context_sha256:
            return TrustStatus.CONTEXT_HASH_MISMATCH
        return TrustStatus.TRUSTED

    @classmethod
    def sign(
        cls,
        *,
        root_private_key: Ed25519PrivateKey,
        root_key_id: str,
        deployment_id: str,
        epoch: int,
        context: GovernanceContext,
        supersedes_hash: str | None,
        issued_at: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> "SignedGovernanceBundle":
        """Administrative constructor. Possession of the private key is the authority."""
        unsigned = {
            "schema": "vinculum.trusted-governance.v0.3",
            "deployment_id": deployment_id,
            "epoch": epoch,
            "root_key_id": root_key_id,
            "context": context.to_dict(include_payload=True),
            "context_sha256": context.sha256(),
            "supersedes_hash": supersedes_hash,
            "issued_at": issued_at,
            "metadata": dict(metadata or {}),
        }
        sig = root_private_key.sign(canonical_json(unsigned).encode("utf-8"))
        return cls(**unsigned, signature_b64=base64.b64encode(sig).decode("ascii"))


@dataclass(frozen=True)
class TrustCheckpoint:
    deployment_id: str
    root_key_id: str
    highest_epoch: int
    current_bundle_sha256: str
    current_context_sha256: str

    def receipt_view(self) -> dict[str, Any]:
        return {
            "schema": "vinculum.trust-checkpoint.v0.3",
            "deployment_id": self.deployment_id,
            "root_key_id": self.root_key_id,
            "highest_epoch": self.highest_epoch,
            "current_bundle_sha256": self.current_bundle_sha256,
            "current_context_sha256": self.current_context_sha256,
        }

    def sha256(self) -> str:
        return sha256_receipt(self.receipt_view())


class CheckpointState(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    READY = "READY"
    LOST = "LOST"
    CORRUPT = "CORRUPT"


@dataclass(frozen=True)
class CheckpointLoad:
    state: CheckpointState
    checkpoint: TrustCheckpoint | None = None
    reason: str = ""


@runtime_checkable
class CheckpointStore(Protocol):
    """Adapter contract for durable monotonic trust state."""

    def initialize(self, *, root: RootTrustAnchor) -> None: ...

    def load(self, *, root: RootTrustAnchor) -> CheckpointLoad: ...

    def commit(self, checkpoint: TrustCheckpoint, *, root: RootTrustAnchor) -> None: ...


class FileCheckpointStore:
    """Atomic, HMAC-authenticated durable trust cursor.

    Two records are maintained:
    * deployment marker: proves the store was initialized before;
    * checkpoint: current monotonic trust cursor.

    If the marker exists but the checkpoint is missing, the state is LOST and normal
    runtime provisioning fails closed. A corrupt marker/checkpoint is CORRUPT.
    """

    def __init__(self, directory: str | os.PathLike[str], *, integrity_key: bytes) -> None:
        if len(integrity_key) < 32:
            raise TrustError("checkpoint integrity_key must be at least 32 bytes")
        self.directory = Path(directory)
        self.integrity_key = bytes(integrity_key)
        self.marker_path = self.directory / "deployment.vinculum.json"
        self.checkpoint_path = self.directory / "checkpoint.vinculum.json"

    def _mac(self, payload: Mapping[str, Any]) -> str:
        return hmac.new(
            self.integrity_key,
            canonical_json(payload).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _encode(self, payload: Mapping[str, Any]) -> bytes:
        envelope = {"payload": dict(payload), "hmac_sha256": self._mac(payload)}
        return (canonical_json(envelope) + "\n").encode("utf-8")

    def _decode(self, raw: bytes) -> dict[str, Any]:
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict) or not isinstance(obj.get("payload"), dict):
            raise TrustError("checkpoint envelope malformed")
        expected = self._mac(obj["payload"])
        actual = str(obj.get("hmac_sha256", ""))
        if not hmac.compare_digest(expected, actual):
            raise TrustError("checkpoint integrity verification failed")
        return obj["payload"]

    def _atomic_write(self, path: Path, data: bytes) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
            # Best-effort directory fsync where the host OS supports it. The file
            # itself has already been fsynced before the atomic replace.
            try:
                flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                dir_fd = os.open(str(self.directory), flags)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError:
                pass
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def initialize(self, *, root: RootTrustAnchor) -> None:
        if self.marker_path.exists() or self.checkpoint_path.exists():
            raise TrustError("checkpoint store is already initialized or contains prior state")
        marker = {
            "schema": "vinculum.deployment-marker.v0.3",
            "deployment_id": root.deployment_id,
            "root_key_id": root.key_id,
            "root_anchor_sha256": root.sha256(),
        }
        self._atomic_write(self.marker_path, self._encode(marker))
        read_back = self._decode(self.marker_path.read_bytes())
        if read_back != marker:
            raise TrustError("deployment marker read-back mismatch")

    def load(self, *, root: RootTrustAnchor) -> CheckpointLoad:
        marker_exists = self.marker_path.exists()
        checkpoint_exists = self.checkpoint_path.exists()
        if not marker_exists and not checkpoint_exists:
            return CheckpointLoad(CheckpointState.UNINITIALIZED)
        if not marker_exists:
            return CheckpointLoad(CheckpointState.CORRUPT, reason="checkpoint exists without deployment marker")
        try:
            marker = self._decode(self.marker_path.read_bytes())
        except Exception as exc:
            return CheckpointLoad(CheckpointState.CORRUPT, reason=f"deployment marker invalid: {exc}")
        if marker.get("deployment_id") != root.deployment_id:
            return CheckpointLoad(CheckpointState.CORRUPT, reason="deployment marker id mismatch")
        if marker.get("root_key_id") != root.key_id or marker.get("root_anchor_sha256") != root.sha256():
            return CheckpointLoad(CheckpointState.CORRUPT, reason="deployment marker root mismatch")
        if not checkpoint_exists:
            return CheckpointLoad(CheckpointState.LOST, reason="initialized deployment has no checkpoint")
        try:
            payload = self._decode(self.checkpoint_path.read_bytes())
            cp = TrustCheckpoint(
                deployment_id=str(payload["deployment_id"]),
                root_key_id=str(payload["root_key_id"]),
                highest_epoch=int(payload["highest_epoch"]),
                current_bundle_sha256=str(payload["current_bundle_sha256"]),
                current_context_sha256=str(payload["current_context_sha256"]),
            )
        except Exception as exc:
            return CheckpointLoad(CheckpointState.CORRUPT, reason=f"checkpoint invalid: {exc}")
        if cp.deployment_id != root.deployment_id or cp.root_key_id != root.key_id:
            return CheckpointLoad(CheckpointState.CORRUPT, reason="checkpoint root/deployment mismatch")
        return CheckpointLoad(CheckpointState.READY, checkpoint=cp)

    def commit(self, checkpoint: TrustCheckpoint, *, root: RootTrustAnchor) -> None:
        pre = self.load(root=root)
        if pre.state not in (CheckpointState.READY, CheckpointState.LOST):
            raise TrustError(f"checkpoint store not initialized/healthy: {pre.state.value}: {pre.reason}")
        payload = checkpoint.receipt_view()
        self._atomic_write(self.checkpoint_path, self._encode(payload))
        post = self.load(root=root)
        if post.state is not CheckpointState.READY or post.checkpoint != checkpoint:
            raise TrustError("checkpoint persistence read-back verification failed")


@dataclass(frozen=True)
class TrustReceipt:
    status: TrustStatus
    deployment_id: str
    root_key_id: str
    epoch: int
    bundle_sha256: str
    context_sha256: str
    checkpoint_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "deployment_id": self.deployment_id,
            "root_key_id": self.root_key_id,
            "epoch": self.epoch,
            "bundle_sha256": self.bundle_sha256,
            "context_sha256": self.context_sha256,
            "checkpoint_sha256": self.checkpoint_sha256,
        }


class TrustedGovernanceRuntime:
    """Read-only-root governance runtime with durable anti-rollback enforcement."""

    def __init__(self, *, root: RootTrustAnchor, checkpoint_store: CheckpointStore) -> None:
        self._root = root
        self._store = checkpoint_store
        self._bundle: SignedGovernanceBundle | None = None
        self._context: GovernanceContext | None = None
        self._receipt: TrustReceipt | None = None

    @property
    def root(self) -> RootTrustAnchor:
        return self._root

    def checkpoint_state(self) -> CheckpointLoad:
        return self._store.load(root=self._root)

    def load_or_advance(self, bundle: SignedGovernanceBundle) -> TrustReceipt:
        sig_status = bundle.verify(self._root)
        if sig_status is not TrustStatus.TRUSTED:
            raise TrustError(sig_status.value)

        state = self._store.load(root=self._root)
        if state.state is CheckpointState.UNINITIALIZED:
            raise TrustError(TrustStatus.UNINITIALIZED.value)
        if state.state is CheckpointState.LOST:
            raise TrustError(TrustStatus.CHECKPOINT_LOST.value)
        if state.state is CheckpointState.CORRUPT or state.checkpoint is None:
            raise TrustError(TrustStatus.CHECKPOINT_CORRUPT.value)

        cp = state.checkpoint
        bundle_hash = bundle.sha256()

        if bundle.epoch < cp.highest_epoch:
            raise TrustError(TrustStatus.ROLLBACK_REJECTED.value)
        if bundle.epoch == cp.highest_epoch:
            if bundle_hash != cp.current_bundle_sha256:
                raise TrustError(TrustStatus.CURRENT_BUNDLE_MISMATCH.value)
            if bundle.context_sha256 != cp.current_context_sha256:
                raise TrustError(TrustStatus.CONTEXT_HASH_MISMATCH.value)
            return self._install(bundle, cp)

        if bundle.epoch != cp.highest_epoch + 1:
            raise TrustError(TrustStatus.EPOCH_GAP.value)
        if bundle.supersedes_hash != cp.current_bundle_sha256:
            raise TrustError(TrustStatus.CHAIN_MISMATCH.value)

        new_cp = TrustCheckpoint(
            deployment_id=self._root.deployment_id,
            root_key_id=self._root.key_id,
            highest_epoch=bundle.epoch,
            current_bundle_sha256=bundle_hash,
            current_context_sha256=bundle.context_sha256,
        )
        try:
            self._store.commit(new_cp, root=self._root)
        except Exception as exc:
            raise TrustError(TrustStatus.CHECKPOINT_WRITE_FAILED.value) from exc
        return self._install(bundle, new_cp)

    def _install(self, bundle: SignedGovernanceBundle, cp: TrustCheckpoint) -> TrustReceipt:
        context = bundle.materialize_context()
        receipt = TrustReceipt(
            status=TrustStatus.TRUSTED,
            deployment_id=self._root.deployment_id,
            root_key_id=self._root.key_id,
            epoch=bundle.epoch,
            bundle_sha256=bundle.sha256(),
            context_sha256=bundle.context_sha256,
            checkpoint_sha256=cp.sha256(),
        )
        self._bundle = bundle
        self._context = context
        self._receipt = receipt
        return receipt

    def require_context(self) -> GovernanceContext:
        if self._context is None:
            raise TrustError("trusted governance context is not loaded")
        return self._context

    def require_receipt(self) -> TrustReceipt:
        if self._receipt is None:
            raise TrustError("trusted governance receipt is not loaded")
        return self._receipt


class TrustedGovernanceBootstrapper:
    """Deployment-only bootstrap surface.

    Normal application runtime should not expose this object. Bootstrap is explicit and
    can only occur against a truly uninitialized durable store.
    """

    def __init__(self, *, root: RootTrustAnchor, checkpoint_store: CheckpointStore) -> None:
        self._root = root
        self._store = checkpoint_store

    def bootstrap(self, bundle: SignedGovernanceBundle) -> TrustReceipt:
        state = self._store.load(root=self._root)
        if state.state is not CheckpointState.UNINITIALIZED:
            raise TrustError(f"bootstrap refused: store state is {state.state.value}")
        status = bundle.verify(self._root)
        if status is not TrustStatus.TRUSTED:
            raise TrustError(status.value)
        if bundle.epoch != 1 or bundle.supersedes_hash is not None:
            raise TrustError("genesis bundle must be epoch 1 with no supersedes_hash")

        self._store.initialize(root=self._root)
        cp = TrustCheckpoint(
            deployment_id=self._root.deployment_id,
            root_key_id=self._root.key_id,
            highest_epoch=1,
            current_bundle_sha256=bundle.sha256(),
            current_context_sha256=bundle.context_sha256,
        )
        try:
            self._store.commit(cp, root=self._root)
        except Exception as exc:
            raise TrustError(TrustStatus.CHECKPOINT_WRITE_FAILED.value) from exc

        runtime = TrustedGovernanceRuntime(root=self._root, checkpoint_store=self._store)
        return runtime.load_or_advance(bundle)


def generate_root_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Administrative/test helper. Never persist the private key in application artifacts."""
    private = Ed25519PrivateKey.generate()
    return private, private.public_key()
