import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.log import append_entry
from app.auth.deps import require_role
from app.database import get_db
from app.models.credential import Credential
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.credential import CredentialCreate, CredentialOut
from app.security.vault import encrypt_password

router = APIRouter()


@router.get("", response_model=list[CredentialOut])
def list_credentials(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester)),
):
    return db.execute(select(Credential).order_by(Credential.label)).scalars().all()


@router.post("", response_model=CredentialOut, status_code=status.HTTP_201_CREATED)
def create_credential(
    payload: CredentialCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester)),
):
    existing = db.execute(select(Credential).where(Credential.label == payload.label)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="a credential set with this label already exists"
        )

    credential = Credential(
        label=payload.label,
        domain=payload.domain,
        username=payload.username,
        encrypted_password=encrypt_password(payload.password),
    )
    db.add(credential)
    db.flush()

    # the password itself is never written to the audit log - only the
    # fact that a credential set was created
    append_entry(
        db,
        actor=user.email,
        event_type="credential_created",
        payload={"credential_id": str(credential.id), "label": credential.label, "username": credential.username},
    )

    db.commit()
    db.refresh(credential)
    return credential


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester)),
):
    credential = db.get(Credential, credential_id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="credential not found")

    append_entry(
        db,
        actor=user.email,
        event_type="credential_deleted",
        payload={"credential_id": str(credential.id), "label": credential.label},
    )

    db.delete(credential)
    db.commit()
