import app.tasks.run_action as run_action_module
from app.models.action import Action
from app.models.audit_log import AuditLogEntry
from app.models.engagement import Engagement
from app.models.enums import ActionStatus, EngagementStatus, RiskTier
from app.tasks.run_action import execute_action


def make_engagement(db) -> Engagement:
    engagement = Engagement(
        name="Run Action Test Engagement",
        scope_validated=True,
        status=EngagementStatus.reconnaissance,
    )
    db.add(engagement)
    db.flush()
    return engagement


class ExplodingAdapter:
    def run(self, adapter_input):
        raise TypeError("expected str, bytes or os.PathLike object, not NoneType")


def test_execute_action_survives_an_adapter_crash_instead_of_getting_stuck(db, monkeypatch):
    monkeypatch.setitem(run_action_module.REGISTRY, "nmap", ExplodingAdapter)

    engagement = make_engagement(db)
    action = Action(
        engagement_id=engagement.id,
        target_id=None,
        tool="nmap",
        params={},
        risk_score=0.4,
        tier=RiskTier.automatic,
        status=ActionStatus.pending,
    )
    db.add(action)
    db.flush()

    execute_action(db, str(action.id))

    db.refresh(action)
    assert action.status == ActionStatus.failed
    assert "unexpected error" in action.result["error"]


def test_execute_action_always_leaves_an_audit_trail_entry(db):
    engagement = make_engagement(db)
    action = Action(
        engagement_id=engagement.id,
        target_id=None,
        tool="unknown-tool",
        params={},
        risk_score=0.4,
        tier=RiskTier.automatic,
        status=ActionStatus.pending,
    )
    db.add(action)
    db.flush()

    execute_action(db, str(action.id))

    db.refresh(action)
    assert action.status == ActionStatus.failed

    entries = db.query(AuditLogEntry).filter(
        AuditLogEntry.event_type == "action_executed"
    ).all()
    assert any(entry.payload.get("action_id") == str(action.id) for entry in entries)


def test_execute_action_with_unresolvable_target_fails_via_the_adapter_itself(db):
    """
    Documents current, real behaviour: submitting an action with no
    resolvable target used to crash the worker outright (TypeError deep
    inside subprocess.run). The API layer now rejects that at creation time
    (see test_submit_action_without_any_target_is_rejected), and the
    unexpected-exception guard in execute_action covers any adapter that
    still manages to raise. This test just pins down what happens if a
    target-less action reaches execute_action anyway, bypassing the API.
    """
    engagement = make_engagement(db)
    action = Action(
        engagement_id=engagement.id,
        target_id=None,
        tool="nmap",
        params={},
        risk_score=0.4,
        tier=RiskTier.automatic,
        status=ActionStatus.pending,
    )
    db.add(action)
    db.flush()

    execute_action(db, str(action.id))

    db.refresh(action)
    assert action.status == ActionStatus.failed
    assert action.result is not None
