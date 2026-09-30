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
from typing import Any, Mapping

from .exceptions import TrustError
from .governance import GovernanceContext
from .receipts import canonical_json, sha256_receipt
from .trust import RootTrustAnchor, SignedGovernanceBundle, TrustCheckpoint, TrustReceipt, TrustStatus


AUTHORITATIVE_PRODUCER = "COMPOSER"


class AuthoritativeState(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    READY = "READY"
    LOST = "LOST"
    CORRUPT = "CORRUPT"


@dataclass(frozen=True)
class ComposerChange:
    """Stable identity for a COMPOSER authoritative-change request.

    `source_system` is intentionally not caller-settable. v0.4's reference choke point is
    specifically COMPOSER -> VINCULUM. Other producers should use a separately reviewed
    adapter rather than relabeling themselves as COMPOSER.
    """

    change_id: str
    artifact_id: str
    revision: str
    actor_id: str = ""
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.change_id.strip():
            raise TrustError("ComposerChange.change_id cannot be empty")
        if not self.artifact_id.strip():
            raise TrustError("ComposerChange.artifact_id cannot be empty")
        if not self.revision.strip():
            raise TrustError("ComposerChange.revision cannot be empty")

    @property
    def source_system(self) -> str:
        return AUTHORITATIVE_PRODUCER

    def receipt_view(self) -> dict[str, Any]:
        return {
            "source_system": self.source_system,
            "change_id": self.change_id,
            "artifact_id": self.artifact_id,
            "revision": self.revision,
            "actor_id": self.actor_id,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }

    def sha256(self) -> str:
        return sha256_receipt(self.receipt_view())


@dataclass(frozen=True)
class CommitIntent:
    """Prepared, signable intent for exactly one authoritative state transition.

    PREPARE reads the current authoritative head and fixes the next epoch and predecessor.
    COMMIT re-reads the head and refuses the intent if anything moved in between.
    """

    change: ComposerChange
    deployment_id: str
    root_key_id: str
    epoch: int
    context: Mapping[str, Any]
    context_sha256: str
    supersedes_hash: str | None
    previous_commit_sha256: str | None
    issued_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema: str = "vinculum.authoritative-intent.v0.4"

    def __post_init__(self) -> None:
        if self.epoch < 1:
            raise TrustError("commit intent epoch must be >= 1")
        if not self.deployment_id.strip() or not self.root_key_id.strip():
            raise TrustError("commit intent deployment/root identity cannot be empty")
        if len(self.context_sha256) != 64:
            raise TrustError("commit intent context_sha256 must be SHA-256")
        if self.epoch == 1:
            if self.supersedes_hash is not None or self.previous_commit_sha256 is not None:
                raise TrustError("genesis intent cannot declare predecessor hashes")
        else:
            if self.supersedes_hash is None or len(self.supersedes_hash) != 64:
                raise TrustError("non-genesis intent requires supersedes_hash")
            if self.previous_commit_sha256 is None or len(self.previous_commit_sha256) != 64:
                raise TrustError("non-genesis intent requires previous_commit_sha256")
        try:
            ctx = GovernanceContext.from_dict(self.context)
        except Exception as exc:
            raise TrustError("commit intent context cannot be materialized") from exc
        if ctx.sha256() != self.context_sha256:
            raise TrustError("commit intent context_sha256 mismatch")

    def intent_view(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "change": self.change.receipt_view(),
            "deployment_id": self.deployment_id,
            "root_key_id": self.root_key_id,
            "epoch": self.epoch,
            "context_sha256": self.context_sha256,
            "supersedes_hash": self.supersedes_hash,
            "previous_commit_sha256": self.previous_commit_sha256,
            "issued_at": self.issued_at,
            "metadata": dict(self.metadata),
        }

    def sha256(self) -> str:
        return sha256_receipt(self.intent_view())

    def _bundle_metadata(self) -> dict[str, Any]:
        return {
            "authoritative_commit": {
                "schema": "vinculum.authoritative-commit-metadata.v0.4",
                "producer": AUTHORITATIVE_PRODUCER,
                "change": self.change.receipt_view(),
                "change_sha256": self.change.sha256(),
                "intent_sha256": self.sha256(),
                "previous_commit_sha256": self.previous_commit_sha256,
            },
            "intent_metadata": dict(self.metadata),
        }

    def unsigned_bundle_view(self) -> dict[str, Any]:
        # The trusted-governance envelope remains v0.3-compatible. v0.4's new semantics
        # live in root-signed metadata instead of silently changing the trust format.
        return {
            "schema": "vinculum.trusted-governance.v0.3",
            "deployment_id": self.deployment_id,
            "epoch": self.epoch,
            "root_key_id": self.root_key_id,
            "context": dict(self.context),
            "context_sha256": self.context_sha256,
            "supersedes_hash": self.supersedes_hash,
            "issued_at": self.issued_at,
            "metadata": self._bundle_metadata(),
        }

    def signing_bytes(self) -> bytes:
        """Bytes to submit to the externally controlled root signer/HSM/KMS."""
        return canonical_json(self.unsigned_bundle_view()).encode("utf-8")

    def attach_signature(self, signature_b64: str) -> SignedGovernanceBundle:
        # SignedGovernanceBundle validates base64 and all core fields.
        return SignedGovernanceBundle(
            **self.unsigned_bundle_view(),
            signature_b64=signature_b64,
        )


@dataclass(frozen=True)
class AuthoritativeCommitReceipt:
    status: str
    deployment_id: str
    root_key_id: str
    epoch: int
    producer: str
    change_id: str
    artifact_id: str
    revision: str
    intent_sha256: str
    bundle_sha256: str
    context_sha256: str
    previous_commit_sha256: str | None
    commit_record_sha256: str
    committed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "deployment_id": self.deployment_id,
            "root_key_id": self.root_key_id,
            "epoch": self.epoch,
            "producer": self.producer,
            "change_id": self.change_id,
            "artifact_id": self.artifact_id,
            "revision": self.revision,
            "intent_sha256": self.intent_sha256,
            "bundle_sha256": self.bundle_sha256,
            "context_sha256": self.context_sha256,
            "previous_commit_sha256": self.previous_commit_sha256,
            "commit_record_sha256": self.commit_record_sha256,
            "committed_at": self.committed_at,
        }

    def sha256(self) -> str:
        return sha256_receipt(self.to_dict())


@dataclass(frozen=True)
class AuthoritativeSnapshot:
    context: GovernanceContext
    bundle: SignedGovernanceBundle
    trust_receipt: TrustReceipt
    commit_receipt: AuthoritativeCommitReceipt

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust": self.trust_receipt.to_dict(),
            "commit": self.commit_receipt.to_dict(),
        }


@dataclass(frozen=True)
class AuthoritativeLoad:
    state: AuthoritativeState
    snapshot: AuthoritativeSnapshot | None = None
    reason: str = ""


class FileAuthoritativeStateStore:
    """Append-only COMPOSER authoritative-state repository.

    One HMAC-protected HEAD points to one immutable, HMAC-protected commit record.
    Commit records carry the complete root-signed governance bundle. A commit record is
    written and fsynced before HEAD moves; a crash before HEAD update can at worst leave
    an unreachable orphan record, never a partially authoritative state.

    This is the reference file adapter, not a substitute for enterprise repository/HSM
    controls. The runtime integrity key is a deployment secret.
    """

    def __init__(self, directory: str | os.PathLike[str], *, integrity_key: bytes) -> None:
        if len(integrity_key) < 32:
            raise TrustError("authoritative store integrity_key must be at least 32 bytes")
        self.directory = Path(directory)
        self.integrity_key = bytes(integrity_key)
        self.marker_path = self.directory / "deployment.authoritative.json"
        self.head_path = self.directory / "HEAD.authoritative.json"
        self.commits_dir = self.directory / "commits"

    def _mac(self, payload: Mapping[str, Any]) -> str:
        return hmac.new(
            self.integrity_key,
            canonical_json(payload).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _encode(self, payload: Mapping[str, Any]) -> bytes:
        env = {"payload": dict(payload), "hmac_sha256": self._mac(payload)}
        return (canonical_json(env) + "\n").encode("utf-8")

    def _decode(self, raw: bytes) -> dict[str, Any]:
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict) or not isinstance(obj.get("payload"), dict):
            raise TrustError("authoritative store envelope malformed")
        expected = self._mac(obj["payload"])
        actual = str(obj.get("hmac_sha256", ""))
        if not hmac.compare_digest(expected, actual):
            raise TrustError("authoritative store integrity verification failed")
        return obj["payload"]

    def _atomic_write(self, path: Path, data: bytes, *, must_not_exist: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if must_not_exist and path.exists():
            # Immutable files may be safely retried only if content is byte-identical.
            if path.read_bytes() == data:
                return
            raise TrustError(f"immutable authoritative record already exists with different content: {path.name}")
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if must_not_exist and path.exists():
                if path.read_bytes() == data:
                    os.unlink(tmp_name)
                    return
                raise TrustError(f"immutable authoritative record raced with different content: {path.name}")
            os.replace(tmp_name, path)
            self._fsync_dir(path.parent)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        try:
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            fd = os.open(str(path), flags)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass

    def _marker(self, root: RootTrustAnchor) -> dict[str, Any]:
        return {
            "schema": "vinculum.authoritative-deployment.v0.4",
            "deployment_id": root.deployment_id,
            "root_key_id": root.key_id,
            "root_anchor_sha256": root.sha256(),
            "producer": AUTHORITATIVE_PRODUCER,
        }

    def _record_path(self, epoch: int, record_sha256: str) -> Path:
        return self.commits_dir / f"{epoch:020d}-{record_sha256}.json"

    @staticmethod
    def _intent_from_record(record: Mapping[str, Any], bundle: SignedGovernanceBundle) -> tuple[ComposerChange, CommitIntent]:
        try:
            change = ComposerChange(**dict(record["change_input"]))
        except Exception as exc:
            raise TrustError("authoritative commit change_input malformed") from exc
        if dict(record.get("change", {})) != change.receipt_view():
            raise TrustError("authoritative commit change receipt mismatch")
        meta = dict(bundle.metadata).get("authoritative_commit", {})
        intent_meta = dict(bundle.metadata).get("intent_metadata", {})
        if not isinstance(meta, Mapping):
            raise TrustError("bundle missing authoritative_commit metadata")
        previous_commit = record.get("previous_commit_sha256")
        intent = CommitIntent(
            change=change,
            deployment_id=bundle.deployment_id,
            root_key_id=bundle.root_key_id,
            epoch=bundle.epoch,
            context=bundle.context,
            context_sha256=bundle.context_sha256,
            supersedes_hash=bundle.supersedes_hash,
            previous_commit_sha256=previous_commit,
            issued_at=bundle.issued_at,
            metadata=intent_meta,
        )
        intent_sha = intent.sha256()
        if str(record.get("intent_sha256", "")) != intent_sha:
            raise TrustError("authoritative commit intent digest mismatch")
        if meta.get("intent_sha256") != intent_sha:
            raise TrustError("bundle/record intent mismatch")
        if meta.get("producer") != AUTHORITATIVE_PRODUCER:
            raise TrustError("bundle producer metadata mismatch")
        if meta.get("change_sha256") != change.sha256():
            raise TrustError("bundle change metadata mismatch")
        if meta.get("previous_commit_sha256") != previous_commit:
            raise TrustError("bundle previous-commit metadata mismatch")
        if bundle.unsigned_view() != intent.unsigned_bundle_view():
            raise TrustError("bundle does not reconstruct from authoritative intent")
        return change, intent

    def inspect(self, *, root: RootTrustAnchor) -> AuthoritativeLoad:
        marker_exists = self.marker_path.exists()
        head_exists = self.head_path.exists()
        if not marker_exists and not head_exists:
            return AuthoritativeLoad(AuthoritativeState.UNINITIALIZED)
        if not marker_exists:
            return AuthoritativeLoad(AuthoritativeState.CORRUPT, reason="HEAD exists without deployment marker")
        try:
            marker = self._decode(self.marker_path.read_bytes())
        except Exception as exc:
            return AuthoritativeLoad(AuthoritativeState.CORRUPT, reason=f"deployment marker invalid: {exc}")
        if marker != self._marker(root):
            return AuthoritativeLoad(AuthoritativeState.CORRUPT, reason="deployment marker root/deployment mismatch")
        if not head_exists:
            return AuthoritativeLoad(AuthoritativeState.LOST, reason="initialized authoritative store has no HEAD")
        try:
            head = self._decode(self.head_path.read_bytes())
            if head.get("schema") != "vinculum.authoritative-head.v0.4":
                raise TrustError("unknown authoritative HEAD schema")
            epoch = int(head["epoch"])
            record_sha = str(head["commit_record_sha256"])
            record_path = self._record_path(epoch, record_sha)
            if not record_path.exists():
                return AuthoritativeLoad(AuthoritativeState.LOST, reason="HEAD commit record is missing")
            record = self._decode(record_path.read_bytes())
            if sha256_receipt(record) != record_sha:
                raise TrustError("commit record digest mismatch")
            if record.get("schema") != "vinculum.authoritative-commit-record.v0.4":
                raise TrustError("unknown authoritative commit record schema")
            bundle = SignedGovernanceBundle(**dict(record["bundle"]))
            if bundle.verify(root) is not TrustStatus.TRUSTED:
                raise TrustError("current authoritative bundle is not trusted by pinned root")
            bundle_sha = bundle.sha256()
            if bundle_sha != record.get("bundle_sha256") or bundle_sha != head.get("bundle_sha256"):
                raise TrustError("authoritative bundle digest mismatch")
            if bundle.context_sha256 != record.get("context_sha256") or bundle.context_sha256 != head.get("context_sha256"):
                raise TrustError("authoritative context digest mismatch")
            if bundle.epoch != epoch:
                raise TrustError("authoritative epoch mismatch")
            change, intent = self._intent_from_record(record, bundle)
            if change.source_system != record.get("producer") or record.get("producer") != AUTHORITATIVE_PRODUCER:
                raise TrustError("authoritative producer mismatch")
            intent_sha = intent.sha256()
            previous_commit = intent.previous_commit_sha256
            context = bundle.materialize_context()
            checkpoint = TrustCheckpoint(
                deployment_id=root.deployment_id,
                root_key_id=root.key_id,
                highest_epoch=bundle.epoch,
                current_bundle_sha256=bundle_sha,
                current_context_sha256=bundle.context_sha256,
            )
            trust = TrustReceipt(
                status=TrustStatus.TRUSTED,
                deployment_id=root.deployment_id,
                root_key_id=root.key_id,
                epoch=bundle.epoch,
                bundle_sha256=bundle_sha,
                context_sha256=bundle.context_sha256,
                checkpoint_sha256=checkpoint.sha256(),
            )
            receipt = AuthoritativeCommitReceipt(
                status="COMMITTED",
                deployment_id=root.deployment_id,
                root_key_id=root.key_id,
                epoch=bundle.epoch,
                producer=AUTHORITATIVE_PRODUCER,
                change_id=change.change_id,
                artifact_id=change.artifact_id,
                revision=change.revision,
                intent_sha256=intent_sha,
                bundle_sha256=bundle_sha,
                context_sha256=bundle.context_sha256,
                previous_commit_sha256=previous_commit,
                commit_record_sha256=record_sha,
                committed_at=str(record.get("committed_at", "")),
            )
            if head.get("commit_receipt_sha256") != receipt.sha256():
                raise TrustError("HEAD commit receipt mismatch")
            return AuthoritativeLoad(
                AuthoritativeState.READY,
                snapshot=AuthoritativeSnapshot(context, bundle, trust, receipt),
            )
        except Exception as exc:
            return AuthoritativeLoad(AuthoritativeState.CORRUPT, reason=f"authoritative state invalid: {exc}")

    def _initialize_marker(self, *, root: RootTrustAnchor) -> None:
        if self.marker_path.exists() or self.head_path.exists():
            raise TrustError("authoritative store is already initialized or contains prior state")
        marker = self._marker(root)
        self._atomic_write(self.marker_path, self._encode(marker), must_not_exist=True)
        if self._decode(self.marker_path.read_bytes()) != marker:
            raise TrustError("authoritative deployment marker read-back mismatch")

    @staticmethod
    def _validate_bundle_matches_intent(intent: CommitIntent, bundle: SignedGovernanceBundle, root: RootTrustAnchor) -> None:
        if bundle.verify(root) is not TrustStatus.TRUSTED:
            raise TrustError("authoritative bundle failed pinned-root verification")
        if bundle.unsigned_view() != intent.unsigned_bundle_view():
            raise TrustError("signed governance bundle does not exactly match prepared commit intent")

    def _record_payload(
        self,
        *,
        intent: CommitIntent,
        bundle: SignedGovernanceBundle,
        committed_at: str,
    ) -> dict[str, Any]:
        return {
            "schema": "vinculum.authoritative-commit-record.v0.4",
            "producer": AUTHORITATIVE_PRODUCER,
            "change_input": {
                "change_id": intent.change.change_id,
                "artifact_id": intent.change.artifact_id,
                "revision": intent.change.revision,
                "actor_id": intent.change.actor_id,
                "reason": intent.change.reason,
                "metadata": dict(intent.change.metadata),
            },
            "change": intent.change.receipt_view(),
            "intent_sha256": intent.sha256(),
            "bundle": bundle.receipt_view(),
            "bundle_sha256": bundle.sha256(),
            "context_sha256": bundle.context_sha256,
            "previous_commit_sha256": intent.previous_commit_sha256,
            "committed_at": committed_at,
        }

    def _write_commit(
        self,
        *,
        root: RootTrustAnchor,
        intent: CommitIntent,
        bundle: SignedGovernanceBundle,
        committed_at: str,
        genesis: bool,
    ) -> AuthoritativeCommitReceipt:
        self._validate_bundle_matches_intent(intent, bundle, root)
        state = self.inspect(root=root)
        if genesis:
            if state.state is not AuthoritativeState.LOST:
                # The marker is deliberately written first. Therefore the only valid
                # pre-commit state after initialization is LOST (marker, no HEAD).
                raise TrustError(f"genesis commit refused: store state is {state.state.value}")
            if intent.epoch != 1 or intent.supersedes_hash is not None or intent.previous_commit_sha256 is not None:
                raise TrustError("invalid genesis commit intent")
        else:
            if state.state is not AuthoritativeState.READY or state.snapshot is None:
                raise TrustError(f"authoritative commit refused: store state is {state.state.value}: {state.reason}")
            # Refuse to extend a repository whose reachable history is incomplete or
            # internally inconsistent. A valid current HEAD is not enough for an
            # authoritative memory system.
            chain = self.verify_chain(root=root)
            if not chain or chain[-1] != state.snapshot.commit_receipt:
                raise TrustError("authoritative history does not terminate at current HEAD")
            current = state.snapshot.commit_receipt
            if intent.epoch != current.epoch + 1:
                raise TrustError("STALE_COMMIT_INTENT: epoch no longer follows authoritative HEAD")
            if intent.supersedes_hash != current.bundle_sha256:
                raise TrustError("STALE_COMMIT_INTENT: supersedes hash no longer matches authoritative HEAD")
            if intent.previous_commit_sha256 != current.commit_record_sha256:
                raise TrustError("STALE_COMMIT_INTENT: previous commit no longer matches authoritative HEAD")

        record = self._record_payload(intent=intent, bundle=bundle, committed_at=committed_at)
        record_sha = sha256_receipt(record)
        receipt = AuthoritativeCommitReceipt(
            status="COMMITTED",
            deployment_id=root.deployment_id,
            root_key_id=root.key_id,
            epoch=bundle.epoch,
            producer=AUTHORITATIVE_PRODUCER,
            change_id=intent.change.change_id,
            artifact_id=intent.change.artifact_id,
            revision=intent.change.revision,
            intent_sha256=intent.sha256(),
            bundle_sha256=bundle.sha256(),
            context_sha256=bundle.context_sha256,
            previous_commit_sha256=intent.previous_commit_sha256,
            commit_record_sha256=record_sha,
            committed_at=committed_at,
        )
        record_path = self._record_path(bundle.epoch, record_sha)
        self._atomic_write(record_path, self._encode(record), must_not_exist=True)
        # Positive persistence proof before HEAD moves.
        if self._decode(record_path.read_bytes()) != record:
            raise TrustError("authoritative commit record read-back mismatch")

        head = {
            "schema": "vinculum.authoritative-head.v0.4",
            "deployment_id": root.deployment_id,
            "root_key_id": root.key_id,
            "epoch": bundle.epoch,
            "bundle_sha256": bundle.sha256(),
            "context_sha256": bundle.context_sha256,
            "commit_record_sha256": record_sha,
            "commit_receipt_sha256": receipt.sha256(),
        }
        self._atomic_write(self.head_path, self._encode(head))
        if self._decode(self.head_path.read_bytes()) != head:
            raise TrustError("authoritative HEAD read-back mismatch")

        post = self.inspect(root=root)
        if post.state is not AuthoritativeState.READY or post.snapshot is None:
            raise TrustError(f"authoritative state failed post-commit verification: {post.state.value}: {post.reason}")
        if post.snapshot.commit_receipt != receipt:
            raise TrustError("authoritative commit receipt read-back mismatch")
        return receipt

    def commit_genesis(
        self,
        *,
        root: RootTrustAnchor,
        intent: CommitIntent,
        bundle: SignedGovernanceBundle,
        committed_at: str = "",
    ) -> AuthoritativeCommitReceipt:
        initial = self.inspect(root=root)
        if initial.state is not AuthoritativeState.UNINITIALIZED:
            raise TrustError(f"authoritative bootstrap refused: store state is {initial.state.value}")
        self._initialize_marker(root=root)
        return self._write_commit(root=root, intent=intent, bundle=bundle, committed_at=committed_at, genesis=True)

    def commit(
        self,
        *,
        root: RootTrustAnchor,
        intent: CommitIntent,
        bundle: SignedGovernanceBundle,
        committed_at: str = "",
    ) -> AuthoritativeCommitReceipt:
        return self._write_commit(root=root, intent=intent, bundle=bundle, committed_at=committed_at, genesis=False)

    def verify_chain(self, *, root: RootTrustAnchor) -> tuple[AuthoritativeCommitReceipt, ...]:
        """Verify every reachable commit from epoch 1 through current HEAD.

        The filename is not trusted. Each record is HMAC-checked, content-hashed, root-
        signature-checked, and predecessor-linked.
        """
        current = self.inspect(root=root)
        if current.state is not AuthoritativeState.READY or current.snapshot is None:
            raise TrustError(f"cannot verify chain: {current.state.value}: {current.reason}")
        expected_record = current.snapshot.commit_receipt.commit_record_sha256
        expected_epoch = current.snapshot.commit_receipt.epoch
        receipts_rev: list[AuthoritativeCommitReceipt] = []
        while expected_epoch >= 1:
            matches = list(self.commits_dir.glob(f"{expected_epoch:020d}-{expected_record}.json"))
            if len(matches) != 1:
                raise TrustError(f"authoritative chain record missing/ambiguous at epoch {expected_epoch}")
            record = self._decode(matches[0].read_bytes())
            if sha256_receipt(record) != expected_record:
                raise TrustError(f"authoritative chain record digest mismatch at epoch {expected_epoch}")
            bundle = SignedGovernanceBundle(**dict(record["bundle"]))
            if bundle.verify(root) is not TrustStatus.TRUSTED:
                raise TrustError(f"authoritative chain signature failure at epoch {expected_epoch}")
            if bundle.epoch != expected_epoch:
                raise TrustError(f"authoritative chain epoch mismatch at epoch {expected_epoch}")
            change, intent = self._intent_from_record(record, bundle)
            receipt = AuthoritativeCommitReceipt(
                status="COMMITTED",
                deployment_id=root.deployment_id,
                root_key_id=root.key_id,
                epoch=bundle.epoch,
                producer=AUTHORITATIVE_PRODUCER,
                change_id=change.change_id,
                artifact_id=change.artifact_id,
                revision=change.revision,
                intent_sha256=intent.sha256(),
                bundle_sha256=bundle.sha256(),
                context_sha256=bundle.context_sha256,
                previous_commit_sha256=intent.previous_commit_sha256,
                commit_record_sha256=expected_record,
                committed_at=str(record.get("committed_at", "")),
            )
            receipts_rev.append(receipt)
            if expected_epoch == 1:
                if receipt.previous_commit_sha256 is not None or bundle.supersedes_hash is not None:
                    raise TrustError("genesis record declares a predecessor")
                break
            prev_record = receipt.previous_commit_sha256
            if prev_record is None:
                raise TrustError(f"authoritative chain missing previous commit at epoch {expected_epoch}")
            # The predecessor bundle digest is separately protected by bundle.supersedes_hash;
            # it will be checked when the predecessor is loaded on the next iteration.
            expected_record = prev_record
            expected_epoch -= 1
        receipts = tuple(reversed(receipts_rev))
        for previous, current_receipt in zip(receipts, receipts[1:]):
            if current_receipt.previous_commit_sha256 != previous.commit_record_sha256:
                raise TrustError("authoritative record chain discontinuity")
            # Resolve the current bundle again to validate supersedes against predecessor bundle.
            p = self._record_path(current_receipt.epoch, current_receipt.commit_record_sha256)
            record = self._decode(p.read_bytes())
            bundle = SignedGovernanceBundle(**dict(record["bundle"]))
            if bundle.supersedes_hash != previous.bundle_sha256:
                raise TrustError("authoritative bundle chain discontinuity")
        return receipts


class AuthoritativeGovernanceRuntime:
    """Read-only runtime view of the committed COMPOSER governance head.

    There is deliberately no `commit`, `advance`, `bootstrap`, or `set_root` surface.
    All writes must traverse AuthoritativeBootstrapService/AuthoritativeCommitService.
    """

    def __init__(
        self,
        *,
        root: RootTrustAnchor,
        store: FileAuthoritativeStateStore,
        verify_chain_on_read: bool = True,
    ) -> None:
        self._root = root
        self._store = store
        self._verify_chain_on_read = bool(verify_chain_on_read)

    @property
    def root(self) -> RootTrustAnchor:
        return self._root

    def snapshot(self) -> AuthoritativeSnapshot:
        loaded = self._store.inspect(root=self._root)
        if loaded.state is AuthoritativeState.UNINITIALIZED:
            raise TrustError("AUTHORITATIVE_UNINITIALIZED")
        if loaded.state is AuthoritativeState.LOST:
            raise TrustError("AUTHORITATIVE_STATE_LOST")
        if loaded.state is AuthoritativeState.CORRUPT or loaded.snapshot is None:
            raise TrustError(f"AUTHORITATIVE_STATE_CORRUPT: {loaded.reason}")
        if self._verify_chain_on_read:
            chain = self._store.verify_chain(root=self._root)
            if not chain or chain[-1] != loaded.snapshot.commit_receipt:
                raise TrustError("AUTHORITATIVE_CHAIN_MISMATCH")
        return loaded.snapshot

    def current_commit(self) -> AuthoritativeCommitReceipt:
        return self.snapshot().commit_receipt


class AuthoritativeBootstrapService:
    """Deployment-only genesis path for the authoritative COMPOSER repository."""

    def __init__(self, *, root: RootTrustAnchor, store: FileAuthoritativeStateStore) -> None:
        self._root = root
        self._store = store

    def prepare_genesis(
        self,
        *,
        change: ComposerChange,
        context: GovernanceContext,
        issued_at: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> CommitIntent:
        state = self._store.inspect(root=self._root)
        if state.state is not AuthoritativeState.UNINITIALIZED:
            raise TrustError(f"authoritative genesis prepare refused: store state is {state.state.value}")
        return CommitIntent(
            change=change,
            deployment_id=self._root.deployment_id,
            root_key_id=self._root.key_id,
            epoch=1,
            context=context.to_dict(include_payload=True),
            context_sha256=context.sha256(),
            supersedes_hash=None,
            previous_commit_sha256=None,
            issued_at=issued_at,
            metadata=dict(metadata or {}),
        )

    def commit_genesis(
        self,
        *,
        intent: CommitIntent,
        signature_b64: str,
        committed_at: str = "",
    ) -> AuthoritativeCommitReceipt:
        if intent.epoch != 1:
            raise TrustError("genesis service accepts only epoch 1 intents")
        bundle = intent.attach_signature(signature_b64)
        return self._store.commit_genesis(
            root=self._root,
            intent=intent,
            bundle=bundle,
            committed_at=committed_at,
        )


class AuthoritativeCommitService:
    """The single reference write choke point after genesis.

    The service never owns the root private key. It prepares exact signing bytes, then
    accepts only a signature over those bytes. This makes HSM/KMS/offline signing the
    natural production deployment pattern.
    """

    def __init__(self, *, root: RootTrustAnchor, store: FileAuthoritativeStateStore) -> None:
        self._root = root
        self._store = store

    def prepare(
        self,
        *,
        change: ComposerChange,
        context: GovernanceContext,
        issued_at: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> CommitIntent:
        state = self._store.inspect(root=self._root)
        if state.state is not AuthoritativeState.READY or state.snapshot is None:
            raise TrustError(f"authoritative prepare refused: store state is {state.state.value}: {state.reason}")
        head = state.snapshot.commit_receipt
        return CommitIntent(
            change=change,
            deployment_id=self._root.deployment_id,
            root_key_id=self._root.key_id,
            epoch=head.epoch + 1,
            context=context.to_dict(include_payload=True),
            context_sha256=context.sha256(),
            supersedes_hash=head.bundle_sha256,
            previous_commit_sha256=head.commit_record_sha256,
            issued_at=issued_at,
            metadata=dict(metadata or {}),
        )

    def commit(
        self,
        *,
        intent: CommitIntent,
        signature_b64: str,
        committed_at: str = "",
    ) -> AuthoritativeCommitReceipt:
        if intent.epoch <= 1:
            raise TrustError("normal authoritative commit service does not accept genesis intents")
        bundle = intent.attach_signature(signature_b64)
        return self._store.commit(
            root=self._root,
            intent=intent,
            bundle=bundle,
            committed_at=committed_at,
        )
