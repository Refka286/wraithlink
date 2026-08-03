import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.suggestion_engine import get_suggestions
from app.audit.log import append_entry
from app.auth.deps import require_role
from app.auth.scoping import get_authorized_engagement
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.suggestion import SuggestionsOut

router = APIRouter()


@router.post("/{engagement_id}", response_model=SuggestionsOut)
def request_suggestions(
    engagement_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester)),
):
    get_authorized_engagement(db, engagement_id, user)

    result = get_suggestions(engagement_id, db)

    append_entry(
        db,
        actor=user.email,
        event_type="ai_suggestions_requested",
        payload={"engagement_id": str(engagement_id)},
    )
    db.commit()

    return result
