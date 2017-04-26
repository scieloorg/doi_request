"""Include Journal Acronym in Deposit

Revision ID: f1e4d34f88dd
Revises:
Create Date: 2017-04-26 11:11:39.865049

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1e4d34f88dd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('deposit', sa.Column('journal_acronym', sa.String(16), index=True))


def downgrade():
    op.drop_column('deposit', 'journal_acronym')
