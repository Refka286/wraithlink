import csv
import io
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.log import append_entry
from app.auth.deps import require_role
from app.auth.scoping import get_authorized_engagement, visible_engagements_query
from app.database import get_db
from app.knowledge.compliance_mapping import format_reference, get_compliance_reference
from app.knowledge.finding_format import format_finding_description
from app.models.action import Action
from app.models.enums import EngagementStatus, UserRole
from app.models.engagement import Engagement
from app.models.engagement_reader import EngagementReader
from app.models.finding import Finding
from app.models.target import Target
from app.models.user import User
from app.schemas.engagement import EngagementCreate, EngagementOut, ReaderGrantCreate, ReaderGrantOut

router = APIRouter()


@router.post("", response_model=EngagementOut, status_code=status.HTTP_201_CREATED)
def create_engagement(
    payload: EngagementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester)),
):
    if not payload.scope_validated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scope_validated must be true to create an engagement",
        )

    engagement = Engagement(
        name=payload.name,
        client_name=payload.client_name,
        scope_validated=True,
        status=EngagementStatus.reconnaissance,
        owner_id=user.id,
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
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester, UserRole.reader)),
):
    query = visible_engagements_query(user).order_by(Engagement.created_at.desc())
    return db.execute(query).scalars().all()


@router.get("/{engagement_id}", response_model=EngagementOut)
def get_engagement(
    engagement_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester, UserRole.reader)),
):
    return get_authorized_engagement(db, engagement_id, user)


@router.get("/{engagement_id}/readers", response_model=list[ReaderGrantOut])
def list_readers(
    engagement_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    get_authorized_engagement(db, engagement_id, user)
    return (
        db.execute(select(EngagementReader).where(EngagementReader.engagement_id == engagement_id))
        .scalars()
        .all()
    )


@router.post("/{engagement_id}/readers", response_model=ReaderGrantOut, status_code=status.HTTP_201_CREATED)
def grant_reader_access(
    engagement_id: uuid.UUID,
    payload: ReaderGrantCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    engagement = get_authorized_engagement(db, engagement_id, user)

    existing = db.execute(
        select(EngagementReader).where(
            EngagementReader.engagement_id == engagement_id,
            EngagementReader.user_id == payload.user_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    grant = EngagementReader(engagement_id=engagement.id, user_id=payload.user_id)
    db.add(grant)

    append_entry(
        db,
        actor=user.email,
        event_type="reader_access_granted",
        payload={"engagement_id": str(engagement_id), "user_id": str(payload.user_id)},
    )

    db.commit()
    db.refresh(grant)
    return grant


@router.delete("/{engagement_id}/readers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_reader_access(
    engagement_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    get_authorized_engagement(db, engagement_id, user)

    grant = db.execute(
        select(EngagementReader).where(
            EngagementReader.engagement_id == engagement_id,
            EngagementReader.user_id == user_id,
        )
    ).scalar_one_or_none()
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such reader grant")

    db.delete(grant)
    append_entry(
        db,
        actor=user.email,
        event_type="reader_access_revoked",
        payload={"engagement_id": str(engagement_id), "user_id": str(user_id)},
    )
    db.commit()


EXPORT_FIELDS = ["type", "severity", "description", "target", "discovered_at", "owasp", "cwe", "reference"]


@router.get("/{engagement_id}/findings/export")
def export_findings(
    engagement_id: uuid.UUID,
    format: str = "csv",
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester, UserRole.reader)),
):
    if format not in ("csv", "json"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be 'csv' or 'json'")

    engagement = get_authorized_engagement(db, engagement_id, user)

    rows = (
        db.execute(
            select(Finding, Action)
            .join(Action, Finding.action_id == Action.id)
            .where(Action.engagement_id == engagement_id)
            .order_by(Finding.created_at)
        )
        .all()
    )
    target_host_by_id = {target.id: target.host for target in engagement.targets}

    records = []
    for finding, action in rows:
        reference = get_compliance_reference(finding.type, finding.description)
        records.append(
            {
                "type": finding.type,
                "severity": finding.severity.value,
                "description": format_finding_description(finding.description),
                "target": target_host_by_id.get(action.target_id, "-"),
                "discovered_at": finding.created_at.isoformat(),
                "owasp": reference.get("owasp") if reference else None,
                "cwe": reference.get("cwe") if reference else None,
                "reference": format_reference(reference),
            }
        )

    filename = f"findings-{engagement_id}.{format}"

    if format == "json":
        content = json.dumps(records, indent=2, ensure_ascii=False)
        media_type = "application/json"
    else:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=EXPORT_FIELDS)
        writer.writeheader()
        writer.writerows(records)
        content = buffer.getvalue()
        media_type = "text/csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
