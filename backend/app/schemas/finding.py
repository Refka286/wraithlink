import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import FindingSeverity


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action_id: uuid.UUID
    type: str
    severity: FindingSeverity
    description: str
    created_at: datetime
