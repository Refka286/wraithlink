import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogEntry
from app.models.mixins import utcnow

GENESIS_HASH = "0" * 64


def compute_hash(actor: str, event_type: str, payload: dict, created_at: str, prev_hash: str) -> str:
    canonical = json.dumps(
        {
            "actor": actor,
            "event_type": event_type,
            "payload": payload,
            "created_at": created_at,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _latest_hash(db: Session) -> str:
    last_entry = db.execute(
        select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc(), AuditLogEntry.id.desc())
    ).scalars().first()
    return last_entry.hash if last_entry is not None else GENESIS_HASH


def append_entry(db: Session, actor: str, event_type: str, payload: dict) -> AuditLogEntry:
    prev_hash = _latest_hash(db)
    created_at = utcnow()
    entry_hash = compute_hash(actor, event_type, payload, created_at.isoformat(), prev_hash)

    entry = AuditLogEntry(
        actor=actor,
        event_type=event_type,
        payload=payload,
        prev_hash=prev_hash,
        hash=entry_hash,
        created_at=created_at,
    )
    db.add(entry)
    db.flush()
    return entry


def verify_chain(entries: list[AuditLogEntry]) -> bool:
    expected_prev = GENESIS_HASH
    for entry in entries:
        if entry.prev_hash != expected_prev:
            return False
        recomputed = compute_hash(
            entry.actor, entry.event_type, entry.payload, entry.created_at.isoformat(), entry.prev_hash
        )
        if recomputed != entry.hash:
            return False
        expected_prev = entry.hash
    return True
