import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit.log import append_entry
from app.auth.deps import require_role
from app.database import get_db
from app.models.action import Action
from app.models.approval import Approval
from app.models.engagement import Engagement
from app.models.enums import ActionStatus, EngagementStatus, UserRole
from app.models.mixins import utcnow
from app.models.user import User
from app.schemas.approval import ApprovalCreate, ApprovalOut
from app.tasks.run_action import run_action_task

router = APIRouter()


@router.post("/{action_id}", response_model=ApprovalOut, status_code=status.HTTP_201_CREATED)
def decide_approval(
    action_id: uuid.UUID,
    payload: ApprovalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.pentester)),
):
    action = db.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="action not found")

    if action.status != ActionStatus.awaiting_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action is not awaiting approval",
        )

    approval = Approval(
        action_id=action.id,
        option_chosen=payload.option_chosen,
        justification=payload.justification,
        approved_by=user.email,
        approved_at=utcnow(),
    )
    db.add(approval)

    action.status = ActionStatus.pending

    engagement = db.get(Engagement, action.engagement_id)
    engagement.status = EngagementStatus.exploitation

    append_entry(
        db,
        actor=user.email,
        event_type="approval_decision",
        payload={
            "action_id": str(action.id),
            "option_chosen": payload.option_chosen.value,
            "justification": payload.justification,
        },
    )

    db.commit()
    db.refresh(approval)

    run_action_task.delay(str(action.id))

    return approval
