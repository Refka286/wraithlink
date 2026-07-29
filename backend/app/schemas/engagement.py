import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import EngagementStatus, TargetType


class TargetCreate(BaseModel):
    host: str
    type: TargetType


class TargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    host: str
    type: TargetType


class EngagementCreate(BaseModel):
    name: str
    scope_validated: bool
    targets: list[TargetCreate] = []


class EngagementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    scope_validated: bool
    status: EngagementStatus
    created_at: datetime
    targets: list[TargetOut] = []
