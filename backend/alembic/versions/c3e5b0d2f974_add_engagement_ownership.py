"""add engagement ownership and reader grants

Revision ID: c3e5b0d2f974
Revises: b2d4a9c1e853
Create Date: 2026-08-02 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3e5b0d2f974'
down_revision: Union[str, Sequence[str], None] = 'b2d4a9c1e853'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('engagements', sa.Column('owner_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_engagements_owner_id_users', 'engagements', 'users', ['owner_id'], ['id']
    )

    op.create_table(
        'engagement_readers',
        sa.Column('engagement_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['engagement_id'], ['engagements.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('engagement_id', 'user_id', name='uq_engagement_reader'),
    )

    # this deployment's existing data pre-dates ownership tracking - migrate
    # the known operator account to admin (per explicit request, so nobody
    # is locked out) and treat it as the historical owner of every
    # engagement created before this migration; environments without that
    # exact account are left with unowned (admin-only-visible) engagements,
    # which is the safe default rather than a migration failure
    op.execute(
        "UPDATE users SET role = 'admin' WHERE email = 'pentester@test.local'"
    )
    op.execute(
        """
        UPDATE engagements
        SET owner_id = (SELECT id FROM users WHERE email = 'pentester@test.local')
        WHERE owner_id IS NULL
        AND EXISTS (SELECT 1 FROM users WHERE email = 'pentester@test.local')
        """
    )


def downgrade() -> None:
    op.drop_table('engagement_readers')
    op.drop_constraint('fk_engagements_owner_id_users', 'engagements', type_='foreignkey')
    op.drop_column('engagements', 'owner_id')
