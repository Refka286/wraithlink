"""add credentials vault and migrate plaintext AD credentials off action params

Revision ID: d4f6c1a8b302
Revises: c3e5b0d2f974
Create Date: 2026-08-02 23:55:00.000000

"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4f6c1a8b302'
down_revision: Union[str, Sequence[str], None] = 'c3e5b0d2f974'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'credentials',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('encrypted_password', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('label'),
    )

    _migrate_plaintext_ad_credentials()


def _migrate_plaintext_ad_credentials() -> None:
    # any pre-existing netexec/bloodhound action ever submitted directly
    # against the API (bypassing the vault, e.g. via curl during earlier
    # testing) would have its username/password sitting in plaintext in
    # actions.params - move those into encrypted credential rows and strip
    # the plaintext from params so history stops leaking secrets too
    key = os.environ.get("CREDENTIALS_ENCRYPTION_KEY")
    if not key:
        # no key configured yet - leave legacy plaintext params untouched
        # rather than failing the whole migration; re-run this cleanup
        # manually (see docs) once CREDENTIALS_ENCRYPTION_KEY is set
        return

    from cryptography.fernet import Fernet

    fernet = Fernet(key.encode())
    conn = op.get_bind()

    rows = conn.execute(
        sa.text(
            "SELECT id, params FROM actions WHERE tool IN ('netexec', 'bloodhound') "
            "AND params ? 'username' AND params ? 'password'"
        )
    ).fetchall()

    if not rows:
        return

    existing_labels = {row[0] for row in conn.execute(sa.text("SELECT label FROM credentials")).fetchall()}
    seen_credentials: dict[tuple[str, str | None, str], str] = {}

    for action_id, raw_params in rows:
        params = raw_params if isinstance(raw_params, dict) else json.loads(raw_params)
        username = params.get("username")
        password = params.get("password")
        domain = params.get("domain")
        if not username or not password:
            continue

        cache_key = (username, domain, password)
        credential_id = seen_credentials.get(cache_key)

        if credential_id is None:
            credential_id = str(uuid.uuid4())
            base_label = f"migrated-{username}" + (f"@{domain}" if domain else "")
            label = base_label
            suffix = 1
            while label in existing_labels:
                suffix += 1
                label = f"{base_label}-{suffix}"
            existing_labels.add(label)

            conn.execute(
                sa.text(
                    "INSERT INTO credentials (id, created_at, label, domain, username, encrypted_password) "
                    "VALUES (:id, :created_at, :label, :domain, :username, :encrypted_password)"
                ),
                {
                    "id": credential_id,
                    "created_at": datetime.now(timezone.utc),
                    "label": label,
                    "domain": domain,
                    "username": username,
                    "encrypted_password": fernet.encrypt(password.encode()).decode(),
                },
            )
            seen_credentials[cache_key] = credential_id

        new_params = dict(params)
        new_params.pop("username", None)
        new_params.pop("password", None)
        new_params.pop("domain", None)
        new_params["credential_id"] = credential_id

        conn.execute(
            sa.text("UPDATE actions SET params = CAST(:params AS jsonb) WHERE id = :id"),
            {"params": json.dumps(new_params), "id": action_id},
        )


def downgrade() -> None:
    op.drop_table('credentials')
