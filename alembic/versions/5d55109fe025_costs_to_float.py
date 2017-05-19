"""costs to float

Revision ID: 5d55109fe025
Revises: 01fb17d68678
Create Date: 2017-05-19 17:06:31.408459

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d55109fe025'
down_revision = '01fb17d68678'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('expenses', sa.Column('cost', sa.Float))


def downgrade():
    pass
