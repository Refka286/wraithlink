"""add engagement client_name

Revision ID: a1c3f8e29d47
Revises: b75a353d3036
Create Date: 2026-08-02 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1c3f8e29d47'
down_revision: Union[str, Sequence[str], None] = 'b75a353d3036'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('engagements', sa.Column('client_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('engagements', 'client_name')
