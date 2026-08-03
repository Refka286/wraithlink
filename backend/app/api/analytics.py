from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.database import get_db
from app.models.action import Action
from app.models.approval import Approval
from app.models.engagement import Engagement
from app.models.enums import UserRole
from app.models.finding import Finding
from app.models.user import User
from app.schemas.analytics import AnalyticsSummaryOut

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummaryOut)
def analytics_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester, UserRole.reader)),
):
    # every metric here is a single aggregate SQL query (COUNT/AVG with
    # GROUP BY) - nothing pulls full row sets into Python to count in a loop,
    # so this stays cheap regardless of how much historical data exists
    total_engagements = db.execute(select(func.count()).select_from(Engagement)).scalar_one()
    total_actions = db.execute(select(func.count()).select_from(Action)).scalar_one()
    total_approvals = db.execute(select(func.count()).select_from(Approval)).scalar_one()

    findings_by_severity = dict(
        db.execute(select(Finding.severity, func.count()).group_by(Finding.severity)).all()
    )
    findings_by_severity = {severity.value: count for severity, count in findings_by_severity.items()}

    tool_usage = dict(db.execute(select(Action.tool, func.count()).group_by(Action.tool)).all())

    tier_distribution = dict(
        db.execute(
            select(Action.tier, func.count()).where(Action.tier.is_not(None)).group_by(Action.tier)
        ).all()
    )
    tier_distribution = {tier.value: count for tier, count in tier_distribution.items()}

    approval_option_ratio = dict(
        db.execute(select(Approval.option_chosen, func.count()).group_by(Approval.option_chosen)).all()
    )
    approval_option_ratio = {option.value: count for option, count in approval_option_ratio.items()}

    average_approval_seconds = db.execute(
        select(func.avg(func.extract("epoch", Approval.approved_at - Action.created_at))).join(
            Action, Approval.action_id == Action.id
        )
    ).scalar_one()

    return AnalyticsSummaryOut(
        total_engagements=total_engagements,
        total_actions=total_actions,
        total_approvals=total_approvals,
        findings_by_severity=findings_by_severity,
        tool_usage=tool_usage,
        tier_distribution=tier_distribution,
        approval_option_ratio=approval_option_ratio,
        average_approval_seconds=float(average_approval_seconds) if average_approval_seconds is not None else None,
    )
