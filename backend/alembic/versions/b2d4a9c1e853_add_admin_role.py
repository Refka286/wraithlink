"""add admin role to userrole enum

Revision ID: b2d4a9c1e853
Revises: a1c3f8e29d47
Create Date: 2026-08-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2d4a9c1e853'
down_revision: Union[str, Sequence[str], None] = 'a1c3f8e29d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # split into its own migration/transaction: Postgres refuses to use a
    # newly-added enum value inside the same transaction that added it, so
    # the value must commit here before the next migration's data backfill
    # (b1's UPDATE ... SET role = 'admin') can reference it
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'admin'")


def downgrade() -> None:
    # Postgres has no direct "remove enum value" - downgrading this
    # migration in place would require rebuilding the type and is not
    # supported here; revert by restoring from a backup taken before upgrade
    pass
