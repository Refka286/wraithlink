import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.scoping import get_authorized_engagement
from app.database import get_db
from app.models.action import Action
from app.models.enums import UserRole
from app.models.finding import Finding
from app.models.user import User
from app.schemas.finding import FindingOut

router = APIRouter()


@router.get("", response_model=list[FindingOut])
def list_findings(
    engagement_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester, UserRole.reader)),
):
    get_authorized_engagement(db, engagement_id, user)
    return (
        db.execute(
            select(Finding)
            .join(Action, Finding.action_id == Action.id)
            .where(Action.engagement_id == engagement_id)
            .order_by(Finding.created_at.desc())
        )
        .scalars()
        .all()
    )
