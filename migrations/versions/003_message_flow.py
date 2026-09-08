"""Add unified message metadata and media assets."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '003_message_flow'
down_revision = '002_telegram_link_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('messages', sa.Column('platform', sa.String(length=20), nullable=False, server_default='web'))
    op.add_column('messages', sa.Column('external_id', sa.String(length=255), nullable=True))
    op.add_column('messages', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
    op.add_column('messages', sa.Column('message_type', sa.String(length=20), nullable=False, server_default='text'))
    op.add_column('messages', sa.Column('status', sa.String(length=20), nullable=False, server_default='completed'))
    op.add_column('messages', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('messages', sa.Column('reply_to_message_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_messages_reply_to_message_id',
        'messages',
        'messages',
        ['reply_to_message_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_messages_platform', 'messages', ['platform'])
    op.create_index('ix_messages_status', 'messages', ['status'])
    op.create_index('ix_messages_reply_to_message_id', 'messages', ['reply_to_message_id'])
    op.create_index(
        'uq_messages_platform_external_id',
        'messages',
        ['platform', 'external_id'],
        unique=True,
        postgresql_where=sa.text('external_id IS NOT NULL'),
    )
    op.create_index(
        'uq_messages_chat_idempotency_key',
        'messages',
        ['chat_id', 'idempotency_key'],
        unique=True,
        postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )
    op.create_table(
        'media_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=False),
        sa.Column('external_file_id', sa.String(length=255), nullable=True),
        sa.Column('storage_key', sa.String(length=512), nullable=True),
        sa.Column('mime_type', sa.String(length=120), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('processing_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_media_assets_message_id', 'media_assets', ['message_id'])
    op.create_index('ix_media_assets_processing_status', 'media_assets', ['processing_status'])
    op.create_index('ix_media_assets_created_at', 'media_assets', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_media_assets_created_at', table_name='media_assets')
    op.drop_index('ix_media_assets_processing_status', table_name='media_assets')
    op.drop_index('ix_media_assets_message_id', table_name='media_assets')
    op.drop_table('media_assets')
    op.drop_index('uq_messages_chat_idempotency_key', table_name='messages')
    op.drop_index('uq_messages_platform_external_id', table_name='messages')
    op.drop_index('ix_messages_reply_to_message_id', table_name='messages')
    op.drop_index('ix_messages_status', table_name='messages')
    op.drop_index('ix_messages_platform', table_name='messages')
    op.drop_constraint('fk_messages_reply_to_message_id', 'messages', type_='foreignkey')
    op.drop_column('messages', 'reply_to_message_id')
    op.drop_column('messages', 'error_message')
    op.drop_column('messages', 'status')
    op.drop_column('messages', 'message_type')
    op.drop_column('messages', 'idempotency_key')
    op.drop_column('messages', 'external_id')
    op.drop_column('messages', 'platform')
