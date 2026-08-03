from pydantic import BaseModel


class AnalyticsSummaryOut(BaseModel):
    total_engagements: int
    total_actions: int
    total_approvals: int
    findings_by_severity: dict[str, int]
    tool_usage: dict[str, int]
    tier_distribution: dict[str, int]
    approval_option_ratio: dict[str, int]
    average_approval_seconds: float | None
