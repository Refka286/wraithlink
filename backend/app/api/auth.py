from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenOut

router = APIRouter()


@router.post("/login", response_model=TokenOut)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == form_data.username)).scalar_one_or_none()

    if user is None or not user.is_active or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    token = create_access_token(subject=user.email, role=user.role.value)
    return TokenOut(access_token=token)
