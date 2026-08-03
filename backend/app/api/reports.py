import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.scoping import get_authorized_engagement
from app.database import get_db
from app.models.enums import UserRole
from app.models.report import Report
from app.models.user import User
from app.reporting.generator import generate_report
from app.schemas.report import ReportOut

router = APIRouter()


@router.post("/{engagement_id}", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    engagement_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester)),
):
    engagement = get_authorized_engagement(db, engagement_id, user)
    return generate_report(db, engagement, actor=user.email)


@router.get("/{report_id}/download")
def download_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester, UserRole.reader)),
):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found")
    get_authorized_engagement(db, report.engagement_id, user)

    pdf_path = Path(report.pdf_ref)
    if not pdf_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report file not found on disk")

    return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)
