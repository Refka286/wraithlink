from app.ai.suggestion_engine import _build_context
from app.models.action import Action
from app.models.engagement import Engagement
from app.models.enums import ActionStatus, EngagementStatus, FindingSeverity, RiskTier, TargetType
from app.models.finding import Finding
from app.models.target import Target

# generous upper bound: with the cap in place, ~40 detail lines plus a
# summary header should stay well under this - the point is to catch a
# regression back to "list every finding", not to pin an exact byte count
MAX_CONTEXT_CHARS = 20000


def test_build_context_caps_size_and_flags_truncation(db):
    # regression for: _build_context() used to list every Finding row with
    # no cap, so a re-scanned engagement with thousands of findings (e.g.
    # ffuf noise before its own baseline filter existed) produced a
    # 700KB+ prompt dominated by noise, drowning out the real signal
    engagement = Engagement(
        name="Large Findings Engagement",
        scope_validated=True,
        status=EngagementStatus.scan,
    )
    db.add(engagement)
    db.flush()

    target = Target(engagement_id=engagement.id, host="10.10.10.5", type=TargetType.web)
    db.add(target)

    action = Action(
        engagement_id=engagement.id,
        target_id=None,
        tool="ffuf",
        params={},
        risk_score=0.6,
        tier=RiskTier.automatic,
        status=ActionStatus.completed,
    )
    db.add(action)
    db.flush()

    findings = [
        Finding(
            action_id=action.id,
            type="discovered_path",
            severity=FindingSeverity.info,
            description=f"url: http://target/path{i} | status: 200 | length: 9903",
        )
        for i in range(5000)
    ]
    db.add_all(findings)
    db.flush()
    db.refresh(engagement)

    context = _build_context(engagement, [action], findings)

    assert len(context) < MAX_CONTEXT_CHARS
    assert "not shown" in context
    # the true total must still be visible even though most rows are capped
    assert "5000" in context


def test_build_context_lists_every_finding_when_under_the_cap(db):
    engagement = Engagement(
        name="Small Findings Engagement",
        scope_validated=True,
        status=EngagementStatus.scan,
    )
    db.add(engagement)
    db.flush()

    target = Target(engagement_id=engagement.id, host="10.10.10.6", type=TargetType.web)
    db.add(target)

    action = Action(
        engagement_id=engagement.id,
        target_id=None,
        tool="nuclei",
        params={},
        risk_score=0.4,
        tier=RiskTier.automatic,
        status=ActionStatus.completed,
    )
    db.add(action)
    db.flush()

    findings = [
        Finding(
            action_id=action.id,
            type="prometheus-metrics",
            severity=FindingSeverity.medium,
            description="matched_at: http://target/metrics | confidence: high",
        )
    ]
    db.add_all(findings)
    db.flush()
    db.refresh(engagement)

    context = _build_context(engagement, [action], findings)

    assert "not shown" not in context
    assert "prometheus-metrics" in context
