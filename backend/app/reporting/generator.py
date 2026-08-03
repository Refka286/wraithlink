import uuid
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.log import append_entry
from app.config import get_settings
from app.knowledge.compliance_mapping import format_reference, get_compliance_reference
from app.knowledge.finding_format import format_finding_description
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

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

SEVERITY_LABELS_FR = {
    "critical": "Critique",
    "high": "Elevee",
    "medium": "Moyenne",
    "low": "Faible",
    "info": "Information",
}

STATUS_LABELS_FR = {
    "scope_validation": "validation du perimetre",
    "reconnaissance": "reconnaissance",
    "scan": "scan",
    "approval_pending": "en attente d'approbation",
    "exploitation": "exploitation",
    "reporting": "rapport",
    "closed": "cloture",
}


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


def _deduplicate_findings(findings: list[Finding]) -> list[dict[str, Any]]:
    # re-running the same scan produces identical findings as separate rows -
    # collapse exact (type, severity, description) duplicates into one row
    # with an occurrence count instead of listing every repeat
    grouped: "OrderedDict[tuple[str, Any, str], dict[str, Any]]" = OrderedDict()
    for finding in findings:
        key = (finding.type, finding.severity, finding.description)
        if key not in grouped:
            grouped[key] = {
                "type": finding.type,
                "severity": finding.severity,
                "description": format_finding_description(finding.description),
                "reference": format_reference(get_compliance_reference(finding.type, finding.description)),
                "count": 0,
            }
        grouped[key]["count"] += 1
    return list(grouped.values())


def _group_findings_by_severity(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_severity: dict[str, list[dict[str, Any]]] = {severity: [] for severity in SEVERITY_ORDER}
    for finding in findings:
        by_severity[finding["severity"].value].append(finding)

    return [
        {
            "severity": severity,
            "label": SEVERITY_LABELS_FR[severity],
            "findings": by_severity[severity],
        }
        for severity in SEVERITY_ORDER
        if by_severity[severity]
    ]


def _actions_with_target(actions: list[Action], targets: list) -> list[dict[str, Any]]:
    target_host_by_id = {target.id: target.host for target in targets}
    return [
        {
            "tool": action.tool,
            "tier": action.tier,
            "risk_score": action.risk_score,
            "status": action.status,
            "target_host": target_host_by_id.get(action.target_id, "-"),
        }
        for action in actions
    ]


def _severity_counts(findings: list[dict[str, Any]]) -> "OrderedDict[str, int]":
    counts: "OrderedDict[str, int]" = OrderedDict((severity, 0) for severity in SEVERITY_ORDER)
    for finding in findings:
        counts[finding["severity"].value] += 1
    return counts


def _risk_posture_summary(counts: "OrderedDict[str, int]", total: int, target_count: int) -> str:
    if total == 0:
        return (
            "Aucune vulnerabilite n'a ete identifiee sur le perimetre teste au cours de cet engagement. "
            "La posture de securite observee apparait satisfaisante a la date du present rapport, sous reserve "
            "des limites de couverture des outils utilises."
        )

    critical, high, medium = counts["critical"], counts["high"], counts["medium"]

    if critical:
        headline = (
            f"{critical} vulnerabilite(s) critique(s) et {high} de severite elevee ont ete identifiees, "
            "exposant le perimetre teste a un risque de compromission immediat."
        )
    elif high:
        headline = (
            f"{high} vulnerabilite(s) de severite elevee ont ete identifiees. Aucune vulnerabilite critique "
            "n'a ete detectee, mais une remediation rapide des points eleves est recommandee."
        )
    elif medium:
        headline = (
            f"{medium} vulnerabilite(s) de severite moyenne ont ete identifiees. Ces constats ne presentent "
            "pas de risque de compromission immediat mais meritent d'etre corriges."
        )
    else:
        headline = (
            "Seules des vulnerabilites de severite faible ou informative ont ete identifiees, sans impact "
            "significatif sur la posture de securite globale du perimetre teste."
        )

    return (
        f"{headline} Au total, {total} constat(s) distinct(s) ont ete recenses sur {target_count} "
        f"cible(s) dans le cadre de cet engagement."
    )


def _date_range(engagement: Engagement, actions: list[Action]) -> str:
    if actions:
        start = min(action.created_at for action in actions)
        end = max(action.created_at for action in actions)
    else:
        start = end = engagement.created_at

    if start.date() == end.date():
        return start.strftime("%d/%m/%Y")
    return f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}"


def _summarize_audit(audit_entries: list[AuditLogEntry]) -> dict[str, Any]:
    # a client/jury deliverable cares about *what was decided and why*, not
    # every internal state transition - show approval decisions in full
    # (they carry the actual accountability trail) and reduce the rest to a
    # count, pointing at the full hash chain as available evidence on request
    approval_decisions = [
        {
            "created_at": entry.created_at,
            "actor": entry.actor,
            "option_chosen": entry.payload.get("option_chosen"),
            "justification": entry.payload.get("justification"),
        }
        for entry in audit_entries
        if entry.event_type == "approval_decision"
    ]
    other_event_counts = Counter(
        entry.event_type for entry in audit_entries if entry.event_type != "approval_decision"
    )

    return {
        "approval_decisions": approval_decisions,
        "total_entries": len(audit_entries),
        "other_event_total": sum(other_event_counts.values()),
    }


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

    raw_findings = (
        db.execute(select(Finding).where(Finding.action_id.in_(action_ids)).order_by(Finding.created_at))
        .scalars()
        .all()
        if action_ids
        else []
    )
    findings = _deduplicate_findings(raw_findings)
    severity_counts = _severity_counts(findings)
    total_findings = sum(severity_counts.values())

    audit_entries = _collect_audit_entries(db, engagement, action_ids)

    generated_at = datetime.now(timezone.utc)

    template = _env.get_template("report.html")
    html_content = template.render(
        engagement=engagement,
        status_label=STATUS_LABELS_FR.get(engagement.status.value, engagement.status.value),
        targets=engagement.targets,
        actions=_actions_with_target(actions, engagement.targets),
        finding_groups=_group_findings_by_severity(findings),
        severity_counts=severity_counts,
        severity_labels=SEVERITY_LABELS_FR,
        total_findings=total_findings,
        total_actions=len(actions),
        risk_posture=_risk_posture_summary(severity_counts, total_findings, len(engagement.targets)),
        date_range=_date_range(engagement, actions),
        audit_summary=_summarize_audit(audit_entries),
        generated_at=generated_at,
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
