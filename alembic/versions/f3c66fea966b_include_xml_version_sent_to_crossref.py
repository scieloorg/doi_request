"""Include XML version sent to crossref

Revision ID: f3c66fea966b
Revises: f647f4269934
Create Date: 2017-04-26 15:24:17.862923

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3c66fea966b'
down_revision = 'f647f4269934'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('deposit', sa.Column('has_submission_xml_valid_references', sa.Boolean, index=True))


def downgrade():
    op.drop_column('deposit', 'has_submission_xml_valid_references')
