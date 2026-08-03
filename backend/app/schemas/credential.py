import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CredentialCreate(BaseModel):
    label: str
    domain: str | None = None
    username: str
    password: str


class CredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    domain: str | None
    username: str
    created_at: datetime
    # deliberately no password/encrypted_password field - this schema is
    # the only shape ever returned by the API, so a decrypted or encrypted
    # password can never leak through a GET response by construction
