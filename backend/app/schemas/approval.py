import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ApprovalOption


class ApprovalCreate(BaseModel):
    option_chosen: ApprovalOption
    justification: str


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action_id: uuid.UUID
    option_chosen: ApprovalOption
    justification: str
    approved_by: str
    approved_at: datetime
