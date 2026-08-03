import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field

from app.knowledge.error_format import shorten_error
from app.models.enums import ActionStatus, RiskTier


class ActionCreate(BaseModel):
    engagement_id: uuid.UUID
    target_id: uuid.UUID | None = None
    tool: str
    params: dict[str, Any] = {}


class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    target_id: uuid.UUID | None
    tool: str
    params: dict[str, Any]
    risk_score: float | None
    tier: RiskTier | None
    status: ActionStatus
    result: dict[str, Any] | None
    created_at: datetime

    @computed_field
    @property
    def error_summary(self) -> str | None:
        raw_error = self.result.get("error") if self.result else None
        return shorten_error(str(raw_error)) if raw_error else None

    @computed_field
    @property
    def note(self) -> str | None:
        raw_note = self.result.get("note") if self.result else None
        return str(raw_note) if raw_note else None
