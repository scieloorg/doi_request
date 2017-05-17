"""indexing deposit_code in logevent

Revision ID: 01fb17d68678
Revises: de7fa8ae6e3f
Create Date: 2017-05-17 09:40:45.262976

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01fb17d68678'
down_revision = 'de7fa8ae6e3f'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('logevent', sa.Column('deposit_code', sa.ForeignKey('deposit.code'), index=True))


def downgrade():
    op.alter_column('logevent', sa.Column('deposit_code', sa.ForeignKey('deposit.code')))
