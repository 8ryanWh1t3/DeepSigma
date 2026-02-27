"""Tests for FEEDS file-bus: Publisher, Subscriber, DLQManager, init_topic_layout."""

import json
from pathlib import Path

import pytest

from core.feeds import FeedTopic, build_envelope, compute_payload_hash
from core.feeds.bus import DLQManager, Publisher, Subscriber, init_topic_layout


SAMPLE_TS_PAYLOAD = {
    "snapshotId": "TS-bus-001",
    "capturedAt": "2026-02-27T10:00:00Z",
    "claims": [{"claimId": "CLAIM-2026-0001"}],
    "evidenceSummary": "Bus test evidence.",
    "coherenceScore": 80,
    "seal": {"hash": "sha256:test", "sealedAt": "2026-02-27T10:00:01Z", "version": 1},
}


def _make_event(event_id="evt-bus-001", topic=FeedTopic.TRUTH_SNAPSHOT, payload=None):
    return build_envelope(
        topic=topic,
        payload=payload or SAMPLE_TS_PAYLOAD,
        packet_id="CP-2026-02-27-0001",
        producer="test-bus",
        event_id=event_id,
    )


class TestInitTopicLayout:
    def test_creates_all_dirs(self, tmp_path):
        root = init_topic_layout(tmp_path)
        for topic in FeedTopic:
            for sub in ("inbox", "processing", "ack", "dlq"):
                assert (root / topic.value / sub).is_dir()

    def test_idempotent(self, tmp_path):
        init_topic_layout(tmp_path)
        init_topic_layout(tmp_path)  # should not raise
        assert (tmp_path / "truth_snapshot" / "inbox").is_dir()

    def test_subset_of_topics(self, tmp_path):
        root = init_topic_layout(tmp_path, topics=[FeedTopic.DRIFT_SIGNAL])
        assert (root / "drift_signal" / "inbox").is_dir()
        assert not (root / "truth_snapshot" / "inbox").exists()


class TestPublisher:
    def test_publish_writes_to_inbox(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        event = _make_event()
        path = pub.publish(FeedTopic.TRUTH_SNAPSHOT, event)
        assert path.exists()
        assert path.parent.name == "inbox"
        assert json.loads(path.read_text())["eventId"] == "evt-bus-001"

    def test_no_tmp_files_remain(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        event = _make_event()
        pub.publish(FeedTopic.TRUTH_SNAPSHOT, event)
        inbox = tmp_topics_root / "truth_snapshot" / "inbox"
        tmp_files = list(inbox.glob(".tmp_*"))
        assert tmp_files == []

    def test_validates_schema(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        bad_event = {"eventId": "test", "topic": "invalid"}
        with pytest.raises(ValueError, match="validation failed"):
            pub.publish(FeedTopic.TRUTH_SNAPSHOT, bad_event)

    def test_publish_multiple_events(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        for i in range(3):
            event = _make_event(event_id=f"evt-bus-{i:03d}")
            pub.publish(FeedTopic.TRUTH_SNAPSHOT, event)
        inbox = tmp_topics_root / "truth_snapshot" / "inbox"
        assert len(list(inbox.glob("*.json"))) == 3

    def test_string_topic_accepted(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        event = _make_event()
        path = pub.publish("truth_snapshot", event)
        assert path.exists()


class TestSubscriber:
    def test_full_lifecycle_inbox_to_ack(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        event = _make_event()
        pub.publish(FeedTopic.TRUTH_SNAPSHOT, event)

        processed = []
        sub = Subscriber(tmp_topics_root, FeedTopic.TRUTH_SNAPSHOT)
        acked = sub.poll(lambda e: processed.append(e["eventId"]))

        assert acked == 1
        assert processed == ["evt-bus-001"]
        assert len(list(sub.ack_dir.glob("*.json"))) == 1
        assert len(list(sub.inbox.glob("*.json"))) == 0
        assert len(list(sub.processing.glob("*.json"))) == 0

    def test_handler_failure_routes_to_dlq(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        event = _make_event()
        pub.publish(FeedTopic.TRUTH_SNAPSHOT, event)

        def _failing_handler(e):
            raise RuntimeError("handler crashed")

        sub = Subscriber(tmp_topics_root, FeedTopic.TRUTH_SNAPSHOT)
        acked = sub.poll(_failing_handler)

        assert acked == 0
        assert len(list(sub.dlq_dir.glob("*.json"))) == 2  # event + error metadata
        assert len(list(sub.inbox.glob("*.json"))) == 0

    def test_batch_size_respected(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        for i in range(5):
            pub.publish(FeedTopic.TRUTH_SNAPSHOT, _make_event(event_id=f"evt-{i:03d}"))

        sub = Subscriber(tmp_topics_root, FeedTopic.TRUTH_SNAPSHOT)
        acked = sub.poll(lambda e: None, batch_size=2)
        assert acked == 2
        assert len(list(sub.inbox.glob("*.json"))) == 3

    def test_empty_inbox_returns_zero(self, tmp_topics_root):
        sub = Subscriber(tmp_topics_root, FeedTopic.TRUTH_SNAPSHOT)
        acked = sub.poll(lambda e: None)
        assert acked == 0

    def test_string_topic_accepted(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        pub.publish(FeedTopic.TRUTH_SNAPSHOT, _make_event())

        sub = Subscriber(tmp_topics_root, "truth_snapshot")
        acked = sub.poll(lambda e: None)
        assert acked == 1


class TestDLQManager:
    def _setup_dlq(self, tmp_topics_root):
        """Publish an event and force it to DLQ via a failing handler."""
        pub = Publisher(tmp_topics_root)
        event = _make_event()
        pub.publish(FeedTopic.TRUTH_SNAPSHOT, event)

        sub = Subscriber(tmp_topics_root, FeedTopic.TRUTH_SNAPSHOT)
        sub.poll(lambda e: (_ for _ in ()).throw(RuntimeError("fail")))
        return DLQManager(tmp_topics_root, FeedTopic.TRUTH_SNAPSHOT)

    def test_list_events(self, tmp_topics_root):
        dlq = self._setup_dlq(tmp_topics_root)
        events = dlq.list_events()
        assert len(events) == 1
        assert events[0].name == "evt-bus-001.json"

    def test_replay_single(self, tmp_topics_root):
        dlq = self._setup_dlq(tmp_topics_root)
        replayed = dlq.replay(event_id="evt-bus-001")
        assert replayed == 1
        assert len(dlq.list_events()) == 0
        assert (dlq.inbox / "evt-bus-001.json").exists()

    def test_replay_all(self, tmp_topics_root):
        pub = Publisher(tmp_topics_root)
        for i in range(3):
            pub.publish(FeedTopic.TRUTH_SNAPSHOT, _make_event(event_id=f"evt-{i:03d}"))

        sub = Subscriber(tmp_topics_root, FeedTopic.TRUTH_SNAPSHOT)
        sub.poll(lambda e: (_ for _ in ()).throw(RuntimeError("fail")), batch_size=3)

        dlq = DLQManager(tmp_topics_root, FeedTopic.TRUTH_SNAPSHOT)
        assert len(dlq.list_events()) == 3
        replayed = dlq.replay()
        assert replayed == 3
        assert len(dlq.list_events()) == 0

    def test_replay_nonexistent_returns_zero(self, tmp_topics_root):
        dlq = DLQManager(tmp_topics_root, FeedTopic.TRUTH_SNAPSHOT)
        assert dlq.replay(event_id="nonexistent") == 0

    def test_purge(self, tmp_topics_root):
        dlq = self._setup_dlq(tmp_topics_root)
        removed = dlq.purge()
        assert removed == 2  # event + error metadata
        assert len(list(dlq.dlq_dir.glob("*.json"))) == 0
