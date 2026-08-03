import json
import uuid
from collections import Counter

import anthropic
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.action import Action
from app.models.engagement import Engagement
from app.models.enums import FindingSeverity
from app.models.finding import Finding

SYSTEM_PROMPT = (
    "You are a pentest assistant helping prioritize next steps. Based on the "
    "engagement scope, actions already run, and findings so far, suggest 2-4 "
    "concrete next actions from this list of available tools: nmap, ffuf, "
    "nuclei, sqlmap, netexec, bloodhound, zap. For each suggestion give: tool "
    "name, reasoning, and priority (high/medium/low). Respond ONLY in JSON: "
    '{"suggestions": [{"tool": "", "reasoning": "", "priority": ""}]}'
)

# a single noisy scan (or a long-running engagement) can produce thousands
# of findings - listing every row would blow up the prompt size and bury
# the genuinely important findings in repetition, so only the highest
# severity / most recent ones are listed individually
MAX_FINDINGS_LISTED = 40

_SEVERITY_RANK = {
    FindingSeverity.critical: 0,
    FindingSeverity.high: 1,
    FindingSeverity.medium: 2,
    FindingSeverity.low: 3,
    FindingSeverity.info: 4,
}


def _summarize_findings(findings: list[Finding]) -> str:
    if not findings:
        return "- none recorded"

    severity_counts = Counter(finding.severity.value for finding in findings)
    type_counts = Counter(finding.type for finding in findings)

    summary_lines = [
        f"Total {len(findings)} finding(s) - by severity: "
        + ", ".join(
            f"{count} {severity}"
            for severity, count in sorted(
                severity_counts.items(), key=lambda kv: _SEVERITY_RANK.get(FindingSeverity(kv[0]), 99)
            )
        ),
        "By type: " + ", ".join(f"{count}x {ftype}" for ftype, count in type_counts.most_common()),
    ]

    ranked = sorted(
        findings,
        key=lambda f: (_SEVERITY_RANK.get(f.severity, 99), -f.created_at.timestamp()),
    )[:MAX_FINDINGS_LISTED]

    detail_lines = [f"- [{f.severity.value}] {f.type}: {f.description}" for f in ranked]

    omitted = len(findings) - len(ranked)
    if omitted > 0:
        detail_lines.append(f"... and {omitted} more finding(s) not shown, see summary above")

    return "\n".join(summary_lines + detail_lines)


def _build_context(engagement: Engagement, actions: list[Action], findings: list[Finding]) -> str:
    scope_lines = [f"- {target.host} ({target.type.value})" for target in engagement.targets] or ["- none recorded"]

    tool_lines = [f"- {action.tool} (status: {action.status.value})" for action in actions] or ["- none run yet"]

    return (
        "Target scope:\n" + "\n".join(scope_lines) + "\n\n"
        "Tools already run:\n" + "\n".join(tool_lines) + "\n\n"
        "Findings so far:\n" + _summarize_findings(findings)
    )


def get_suggestions(engagement_id: uuid.UUID, db: Session) -> dict:
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="engagement not found")

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

    context = _build_context(engagement, actions, findings)

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text")

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI response was not valid JSON",
        ) from exc
