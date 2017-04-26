"""Becoming journal_acronym nullable false

Revision ID: f647f4269934
Revises: f1e4d34f88dd
Create Date: 2017-04-26 11:42:30.210810

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
revision = 'f647f4269934'
down_revision = 'f1e4d34f88dd'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    session.query(depositor.Deposit).filter_by(journal_acronym=None).update({"journal_acronym": "undefined"})
    op.alter_column('deposit', sa.Column('journal_acronym', sa.String(16), nullable=False, index=True))


def downgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    op.alter_column('deposit', sa.Column('journal_acronym', sa.String(16), nullable=False, index=True))
    session.query(depositor.Deposit).filter_by(journal_acronym='undefined').update({"journal_acronym": None})
