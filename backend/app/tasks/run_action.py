from sqlalchemy.orm import Session

from app.adapters import REGISTRY
from app.adapters.base import AdapterInput
from app.audit.log import append_entry
from app.database import SessionLocal
from app.models.action import Action
from app.models.credential import Credential
from app.models.enums import ActionStatus, FindingSeverity
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.target import Target
from app.security.vault import decrypt_password
from app.tasks.celery_app import celery_app


def _severity_from(raw: str | None) -> FindingSeverity:
    try:
        return FindingSeverity(raw)
    except ValueError:
        return FindingSeverity.info


def _resolve_params(db: Session, params: dict) -> dict:
    """
    Build the params dict actually handed to the adapter. If the action
    references a saved credential set by id, the decrypted username/
    password/domain are merged into a COPY here - never written back onto
    the Action row, so the plaintext password only ever exists in memory
    for the duration of this one adapter call.
    """
    credential_id = params.get("credential_id")
    if not credential_id:
        return params

    credential = db.get(Credential, credential_id)
    if credential is None:
        raise ValueError(f"no saved credential set found for id '{credential_id}'")

    resolved = dict(params)
    resolved["username"] = credential.username
    resolved["password"] = decrypt_password(credential.encrypted_password)
    if credential.domain:
        resolved["domain"] = credential.domain
    return resolved


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
            params=_resolve_params(db, action.params),
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


@celery_app.task(name="wraithlink.run_action")
def run_action_task(action_id: str) -> None:
    db = SessionLocal()
    try:
        execute_action(db, action_id)
    finally:
        db.close()
