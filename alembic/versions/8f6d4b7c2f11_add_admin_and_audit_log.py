"""add admin flag and audit log

Revision ID: 8f6d4b7c2f11
Revises: 6f3d3c0f3a2a
Create Date: 2026-03-11 22:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '8f6d4b7c2f11'
down_revision = '6f3d3c0f3a2a'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column['name'] for column in inspector.get_columns('user_account')}

    if 'is_admin' not in user_columns:
        op.add_column(
            'user_account',
            sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.execute('UPDATE user_account SET is_admin = true')
        op.alter_column('user_account', 'is_admin', server_default=None)

    user_indexes = {index['name'] for index in inspector.get_indexes('user_account')}
    if 'ix_user_account_is_admin' not in user_indexes:
        op.create_index('ix_user_account_is_admin', 'user_account', ['is_admin'], unique=False)

    table_names = set(inspector.get_table_names())
    if 'audit_log' not in table_names:
        op.create_table(
            'audit_log',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('actor_user_id', sa.Integer(), nullable=True),
            sa.Column('actor_username', sa.String(length=64), nullable=True),
            sa.Column('action', sa.String(length=64), nullable=False),
            sa.Column('target_type', sa.String(length=64), nullable=True),
            sa.Column('target_id', sa.String(length=64), nullable=True),
            sa.Column('target_label', sa.String(length=255), nullable=True),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['actor_user_id'], ['user_account.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    inspector = sa.inspect(bind)
    audit_indexes = {index['name'] for index in inspector.get_indexes('audit_log')}
    if 'ix_audit_log_action' not in audit_indexes:
        op.create_index('ix_audit_log_action', 'audit_log', ['action'], unique=False)
    if 'ix_audit_log_actor_user_id' not in audit_indexes:
        op.create_index('ix_audit_log_actor_user_id', 'audit_log', ['actor_user_id'], unique=False)
    if 'ix_audit_log_actor_username' not in audit_indexes:
        op.create_index('ix_audit_log_actor_username', 'audit_log', ['actor_username'], unique=False)
    if 'ix_audit_log_created_at' not in audit_indexes:
        op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'], unique=False)
    if 'ix_audit_log_target_id' not in audit_indexes:
        op.create_index('ix_audit_log_target_id', 'audit_log', ['target_id'], unique=False)
    if 'ix_audit_log_target_type' not in audit_indexes:
        op.create_index('ix_audit_log_target_type', 'audit_log', ['target_type'], unique=False)


def downgrade():
    op.drop_index('ix_audit_log_target_type', table_name='audit_log')
    op.drop_index('ix_audit_log_target_id', table_name='audit_log')
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_actor_username', table_name='audit_log')
    op.drop_index('ix_audit_log_actor_user_id', table_name='audit_log')
    op.drop_index('ix_audit_log_action', table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_index('ix_user_account_is_admin', table_name='user_account')
    op.drop_column('user_account', 'is_admin')
