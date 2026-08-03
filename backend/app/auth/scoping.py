import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement
from app.models.engagement_reader import EngagementReader
from app.models.enums import UserRole
from app.models.user import User


def can_access_engagement(db: Session, engagement: Engagement, user: User) -> bool:
    if user.role == UserRole.admin:
        return True
    if user.role == UserRole.pentester:
        return engagement.owner_id == user.id
    if user.role == UserRole.reader:
        grant = db.execute(
            select(EngagementReader).where(
                EngagementReader.engagement_id == engagement.id,
                EngagementReader.user_id == user.id,
            )
        ).scalar_one_or_none()
        return grant is not None
    return False


def get_authorized_engagement(db: Session, engagement_id: uuid.UUID, user: User) -> Engagement:
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="engagement not found")
    if not can_access_engagement(db, engagement, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized for this engagement")
    return engagement


def visible_engagements_query(user: User) -> Select:
    """A SELECT scoped to the engagements this user is allowed to list."""
    if user.role == UserRole.admin:
        return select(Engagement)
    if user.role == UserRole.pentester:
        return select(Engagement).where(Engagement.owner_id == user.id)
    if user.role == UserRole.reader:
        return (
            select(Engagement)
            .join(EngagementReader, EngagementReader.engagement_id == Engagement.id)
            .where(EngagementReader.user_id == user.id)
        )
    return select(Engagement).where(False)
