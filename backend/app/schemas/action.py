import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

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
