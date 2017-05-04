"""expenses model

Revision ID: 94ff13ef2750
Revises: bdf99d8eeb57
Create Date: 2017-05-02 11:47:24.142971

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '94ff13ef2750'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    op.alter_column('eventlog', sa.Column('date', sa.DateTime(timezone=True)))
    op.alter_column('expenses', sa.Column('registry_date', sa.DateTime(timezone=True)))


def downgrade():

    op.alter_column('eventlog', sa.Column('date', sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now()))
    op.alter_column('expenses', sa.Column('registry_date', sa.DateTime(timezone=True), default=datetime.utcnow, server_default=func.now()))
