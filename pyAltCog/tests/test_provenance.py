from pyaltcog.provenance import AuditLedger


def test_hash_chain_verifies():
    l = AuditLedger()
    l.append(event_type="A", occurred_at="t1", subject_id="S", payload={"x": 1})
    l.append(event_type="B", occurred_at="t2", subject_id="S", payload={"x": 2})
    assert l.verify()


def test_tampered_event_fails():
    l = AuditLedger()
    e = l.append(event_type="A", occurred_at="t1", subject_id="S", payload={"x": 1})
    object.__setattr__(e, "event_hash", "bad")
    assert not l.verify()
