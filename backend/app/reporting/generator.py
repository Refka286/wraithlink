import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.log import append_entry
from app.config import get_settings
from app.models.action import Action
from app.models.audit_log import AuditLogEntry
from app.models.engagement import Engagement
from app.models.finding import Finding
from app.models.report import Report

TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _collect_audit_entries(db: Session, engagement: Engagement, action_ids: list[uuid.UUID]) -> list[AuditLogEntry]:
    action_id_strings = {str(action_id) for action_id in action_ids}
    engagement_id_string = str(engagement.id)

    entries = db.execute(select(AuditLogEntry).order_by(AuditLogEntry.created_at)).scalars().all()
    return [
        entry
        for entry in entries
        if entry.payload.get("engagement_id") == engagement_id_string
        or entry.payload.get("action_id") in action_id_strings
    ]


def generate_report(db: Session, engagement: Engagement, actor: str) -> Report:
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:
        # OSError covers the common case on hosts missing the native
        # Pango/GObject libraries weasyprint's cffi bindings dlopen at
        # import time (e.g. plain Windows without the GTK runtime) -
        # the Docker image installs those, so this only bites local dev.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF rendering is unavailable on this host (weasyprint native dependencies missing)",
        ) from exc

    actions = (
        db.execute(select(Action).where(Action.engagement_id == engagement.id).order_by(Action.created_at))
        .scalars()
        .all()
    )
    action_ids = [action.id for action in actions]

    findings = (
        db.execute(select(Finding).where(Finding.action_id.in_(action_ids)).order_by(Finding.created_at))
        .scalars()
        .all()
        if action_ids
        else []
    )

    audit_entries = _collect_audit_entries(db, engagement, action_ids)

    template = _env.get_template("report.html")
    html_content = template.render(
        engagement=engagement,
        targets=engagement.targets,
        actions=actions,
        findings=findings,
        audit_entries=audit_entries,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    settings = get_settings()
    output_dir = Path(settings.evidence_storage_path) / str(engagement.id) / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"report-{uuid.uuid4().hex[:8]}.pdf"

    HTML(string=html_content).write_pdf(str(output_path))

    report = Report(engagement_id=engagement.id, pdf_ref=str(output_path))
    db.add(report)

    append_entry(
        db,
        actor=actor,
        event_type="report_generated",
        payload={"engagement_id": str(engagement.id), "report_path": str(output_path)},
    )

    db.commit()
    db.refresh(report)
    return report
