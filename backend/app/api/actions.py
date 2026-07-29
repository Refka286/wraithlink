import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.log import append_entry
from app.auth.deps import require_role
from app.database import get_db
from app.models.action import Action
from app.models.engagement import Engagement
from app.models.enums import ActionStatus, RiskTier, UserRole
from app.models.user import User
from app.risk_engine.engine import classify_action
from app.risk_engine.catalog import UnknownActionRatingError
from app.schemas.action import ActionCreate, ActionOut
from app.state_machine.engagement import next_status_after_action
from app.tasks.run_action import run_action_task

router = APIRouter()

DEFAULT_PROFILES = {
    "nmap": "syn-stealth",
    "ffuf": "default",
    "nuclei": "default",
    "sqlmap": "aggressive",
    "netexec": "kerberoast",
    "bloodhound": "collect",
    "zap": "active-scan",
}


@router.post("", response_model=ActionOut, status_code=status.HTTP_201_CREATED)
def submit_action(
    payload: ActionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.pentester)),
):
    engagement = db.get(Engagement, payload.engagement_id)
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="engagement not found")

    profile = payload.params.get("profile", DEFAULT_PROFILES.get(payload.tool, "default"))

    try:
        score, tier, _ = classify_action(payload.tool, profile)
    except UnknownActionRatingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    action = Action(
        engagement_id=engagement.id,
        target_id=payload.target_id,
        tool=payload.tool,
        params=payload.params,
        risk_score=score,
        tier=tier,
        status=ActionStatus.blocked if tier == RiskTier.forbidden else ActionStatus.pending,
    )
    db.add(action)
    db.flush()

    if tier == RiskTier.forbidden:
        append_entry(
            db,
            actor=user.email,
            event_type="action_blocked",
            payload={"action_id": str(action.id), "tool": action.tool, "score": score},
        )
        db.commit()
        db.refresh(action)
        return action

    engagement.status = next_status_after_action(engagement.status, tier)

    if tier == RiskTier.approval:
        action.status = ActionStatus.awaiting_approval

    append_entry(
        db,
        actor=user.email,
        event_type="action_submitted",
        payload={"action_id": str(action.id), "tool": action.tool, "tier": tier.value, "score": score},
    )

    db.commit()
    db.refresh(action)

    if tier == RiskTier.automatic:
        run_action_task.delay(str(action.id))

    return action


@router.get("", response_model=list[ActionOut])
def list_actions(
    engagement_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.pentester, UserRole.reader)),
):
    return (
        db.execute(
            select(Action).where(Action.engagement_id == engagement_id).order_by(Action.created_at.desc())
        )
        .scalars()
        .all()
    )


@router.get("/{action_id}", response_model=ActionOut)
def get_action(
    action_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.pentester, UserRole.reader)),
):
    action = db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="action not found")
    return action
