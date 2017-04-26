"""Include XML version sent to crossref, set default value and nullable False

Revision ID: bdf99d8eeb57
Revises: f3c66fea966b
Create Date: 2017-04-26 15:28:30.462856

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session as BaseSession, relationship

from doi_request.models import depositor

Session = sessionmaker()
Base = declarative_base()

# revision identifiers, used by Alembic.
revision = 'bdf99d8eeb57'
down_revision = 'f3c66fea966b'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    session.query(depositor.Deposit).filter_by(has_submission_xml_valid_references=None).update({"has_submission_xml_valid_references": False})
    op.alter_column('deposit', sa.Column('has_submission_xml_valid_references', sa.Boolean, nullable=False, index=True))


def downgrade():
    pass
