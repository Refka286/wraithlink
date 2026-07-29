import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.log import append_entry
from app.auth.deps import require_role
from app.database import get_db
from app.models.enums import EngagementStatus, UserRole
from app.models.engagement import Engagement
from app.models.target import Target
from app.models.user import User
from app.schemas.engagement import EngagementCreate, EngagementOut

router = APIRouter()


@router.post("", response_model=EngagementOut, status_code=status.HTTP_201_CREATED)
def create_engagement(
    payload: EngagementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.pentester)),
):
    if not payload.scope_validated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scope_validated must be true to create an engagement",
        )

    engagement = Engagement(
        name=payload.name,
        scope_validated=True,
        status=EngagementStatus.reconnaissance,
    )
    for target in payload.targets:
        engagement.targets.append(Target(host=target.host, type=target.type))

    db.add(engagement)
    db.flush()

    append_entry(
        db,
        actor=user.email,
        event_type="engagement_created",
        payload={"engagement_id": str(engagement.id), "name": engagement.name},
    )

    db.commit()
    db.refresh(engagement)
    return engagement


@router.get("", response_model=list[EngagementOut])
def list_engagements(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.pentester, UserRole.reader)),
):
    return db.execute(select(Engagement).order_by(Engagement.created_at.desc())).scalars().all()


@router.get("/{engagement_id}", response_model=EngagementOut)
def get_engagement(
    engagement_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.pentester, UserRole.reader)),
):
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="engagement not found")
    return engagement
