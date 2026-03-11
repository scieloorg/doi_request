"""add user account table

Revision ID: 6f3d3c0f3a2a
Revises: 01fb17d68678
Create Date: 2026-03-11 22:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '6f3d3c0f3a2a'
down_revision = '01fb17d68678'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_account',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('ix_user_account_is_active', 'user_account', ['is_active'], unique=False)
    op.create_index('ix_user_account_username', 'user_account', ['username'], unique=False)


def downgrade():
    op.drop_index('ix_user_account_username', table_name='user_account')
    op.drop_index('ix_user_account_is_active', table_name='user_account')
    op.drop_table('user_account')
