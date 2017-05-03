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

    op.add_column('deposit', sa.Column('publication_year', sa.Integer, index=True))

    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('retro', sa.Boolean, nullable=False, index=True),
        sa.Column('publication_year', sa.Integer, index=True),
        sa.Column('registry_date', sa.DateTime(timezone=True), default=datetime.utcnow, server_default=sa.func.now()),
        sa.Column('doi', sa.String(128), index=True),
        sa.Column('cost', sa.Float, nullable=False)
    )


def downgrade():
    op.drop_column('deposit', 'publication_year')
    op.drop_table('expenses')
