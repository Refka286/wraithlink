import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.database import get_db
from app.models.engagement import Engagement
from app.models.enums import UserRole
from app.models.user import User
from app.reporting.generator import generate_report
from app.schemas.report import ReportOut

router = APIRouter()


@router.post("/{engagement_id}", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    engagement_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.pentester)),
):
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="engagement not found")

    return generate_report(db, engagement, actor=user.email)
