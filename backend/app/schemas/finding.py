import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.knowledge.compliance_mapping import format_reference, get_compliance_reference
from app.models.enums import FindingSeverity


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action_id: uuid.UUID
    type: str
    severity: FindingSeverity
    description: str
    created_at: datetime

    @computed_field
    @property
    def compliance_reference(self) -> str:
        return format_reference(get_compliance_reference(self.type, self.description))
