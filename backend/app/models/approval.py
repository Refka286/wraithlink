import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ApprovalOption
from app.models.mixins import UUIDPrimaryKeyMixin


class Approval(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "approvals"

    action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("actions.id"), nullable=False, unique=True
    )
    option_chosen: Mapped[ApprovalOption] = mapped_column(nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    action: Mapped["Action"] = relationship(back_populates="approval")
