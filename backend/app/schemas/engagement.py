import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import EngagementStatus, TargetType


class TargetCreate(BaseModel):
    host: str
    type: TargetType

    @field_validator("host")
    @classmethod
    def strip_host(cls, value: str) -> str:
        return value.strip()


class TargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    host: str
    type: TargetType


class EngagementCreate(BaseModel):
    name: str
    client_name: str | None = None
    scope_validated: bool
    targets: list[TargetCreate] = []


class EngagementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    client_name: str | None
    scope_validated: bool
    status: EngagementStatus
    created_at: datetime
    owner_id: uuid.UUID | None
    targets: list[TargetOut] = []


class ReaderGrantCreate(BaseModel):
    user_id: uuid.UUID


class ReaderGrantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
