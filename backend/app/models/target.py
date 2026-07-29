import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TargetType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Target(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "targets"

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=False
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[TargetType] = mapped_column(nullable=False)

    engagement: Mapped["Engagement"] = relationship(back_populates="targets")
