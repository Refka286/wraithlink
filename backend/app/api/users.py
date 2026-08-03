from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.log import append_entry
from app.auth.deps import require_role
from app.auth.security import hash_password
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import UserCreate, UserOut

router = APIRouter()


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    return db.execute(select(User).order_by(User.created_at)).scalars().all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="a user with this email already exists")

    new_user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(new_user)
    db.flush()

    append_entry(
        db,
        actor=user.email,
        event_type="user_created",
        payload={"user_id": str(new_user.id), "email": new_user.email, "role": new_user.role.value},
    )

    db.commit()
    db.refresh(new_user)
    return new_user
