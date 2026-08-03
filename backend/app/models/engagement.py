import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EngagementStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Engagement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "engagements"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scope_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[EngagementStatus] = mapped_column(
        default=EngagementStatus.scope_validation, nullable=False
    )
    # nullable to accommodate engagements that pre-date ownership tracking -
    # an engagement with no owner is only visible to admins (see app/auth/scoping.py)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    targets: Mapped[list["Target"]] = relationship(
        back_populates="engagement", cascade="all, delete-orphan"
    )
    actions: Mapped[list["Action"]] = relationship(
        back_populates="engagement", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="engagement", cascade="all, delete-orphan"
    )
