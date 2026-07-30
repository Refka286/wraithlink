from sqlalchemy.orm import Session

from app.adapters import REGISTRY
from app.adapters.base import AdapterInput
from app.audit.log import append_entry
from app.database import SessionLocal
from app.models.action import Action
from app.models.enums import ActionStatus, FindingSeverity
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.target import Target
from app.tasks.celery_app import celery_app


def _severity_from(raw: str | None) -> FindingSeverity:
    try:
        return FindingSeverity(raw)
    except ValueError:
        return FindingSeverity.info


def execute_action(db: Session, action_id: str) -> None:
    action = db.get(Action, action_id)
    if action is None:
        return

    adapter_cls = REGISTRY.get(action.tool)
    if adapter_cls is None:
        action.status = ActionStatus.failed
        action.result = {"error": f"no adapter registered for tool '{action.tool}'"}
        append_entry(
            db,
            actor="system",
            event_type="action_executed",
            payload={"action_id": str(action.id), "status": action.status.value},
        )
        db.commit()
        return

    target = db.get(Target, action.target_id) if action.target_id else None
    target_host = target.host if target else action.params.get("target")

    action.status = ActionStatus.running
    db.commit()

    try:
        adapter_input = AdapterInput(
            tool=action.tool,
            target=target_host,
            params=action.params,
            risk_tier=action.tier.value if action.tier else "unknown",
            engagement_id=str(action.engagement_id),
        )

        output = adapter_cls().run(adapter_input)

        action.status = ActionStatus.completed if output.status == "success" else ActionStatus.failed
        action.result = output.to_dict()

        for ref in output.evidence:
            db.add(Evidence(action_id=action.id, storage_ref=ref, type="raw_tool_output"))

        for parsed in output.parsed_findings:
            db.add(
                Finding(
                    action_id=action.id,
                    type=parsed.get("type", "unknown"),
                    severity=_severity_from(parsed.get("severity")),
                    description=str(parsed),
                )
            )
    except Exception as exc:
        # an action must always reach a terminal state - never leave it
        # stuck at 'running' because of a bug or an unexpected adapter
        # crash, the audit trail depends on every action being resolved
        action.status = ActionStatus.failed
        action.result = {"error": f"unexpected error during execution: {exc}"}

    append_entry(
        db,
        actor="system",
        event_type="action_executed",
        payload={"action_id": str(action.id), "status": action.status.value},
    )

    db.commit()


@celery_app.task(name="aegispen.run_action")
def run_action_task(action_id: str) -> None:
    db = SessionLocal()
    try:
        execute_action(db, action_id)
    finally:
        db.close()
