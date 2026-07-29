import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EngagementStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Engagement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "engagements"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[EngagementStatus] = mapped_column(
        default=EngagementStatus.scope_validation, nullable=False
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
