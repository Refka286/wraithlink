from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Credential(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "credentials"

    label: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    # Fernet ciphertext, never the plaintext password - see app/security/vault.py
    encrypted_password: Mapped[str] = mapped_column(String, nullable=False)
