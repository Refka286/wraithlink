from app.audit.log import GENESIS_HASH, append_entry, verify_chain


def test_first_entry_chains_from_genesis(db):
    entry = append_entry(db, actor="tester", event_type="engagement_created", payload={"name": "demo"})

    assert entry.prev_hash == GENESIS_HASH
    assert len(entry.hash) == 64


def test_entries_chain_sequentially(db):
    first = append_entry(db, actor="tester", event_type="engagement_created", payload={"name": "demo"})
    second = append_entry(db, actor="tester", event_type="action_submitted", payload={"tool": "nmap"})

    assert second.prev_hash == first.hash
    assert verify_chain([first, second]) is True


def test_verify_chain_detects_tampering(db):
    first = append_entry(db, actor="tester", event_type="engagement_created", payload={"name": "demo"})
    second = append_entry(db, actor="tester", event_type="action_submitted", payload={"tool": "nmap"})

    second.payload = {"tool": "tampered"}

    assert verify_chain([first, second]) is False
