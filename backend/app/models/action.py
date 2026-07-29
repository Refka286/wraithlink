import uuid

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ActionStatus, RiskTier
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Action(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "actions"

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=False
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("targets.id"), nullable=True
    )
    tool: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)

    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tier: Mapped[RiskTier | None] = mapped_column(nullable=True)
    status: Mapped[ActionStatus] = mapped_column(default=ActionStatus.pending, nullable=False)

    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    engagement: Mapped["Engagement"] = relationship(back_populates="actions")
    approval: Mapped["Approval | None"] = relationship(
        back_populates="action", uselist=False, cascade="all, delete-orphan"
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="action", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="action", cascade="all, delete-orphan"
    )
