"""Add one-time tokens for website and Telegram account linking."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_telegram_link_tokens'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'telegram_link_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_telegram_link_tokens_token_hash', 'telegram_link_tokens', ['token_hash'], unique=True)
    op.create_index('ix_telegram_link_tokens_user_id', 'telegram_link_tokens', ['user_id'])
    op.create_index('ix_telegram_link_tokens_telegram_id', 'telegram_link_tokens', ['telegram_id'])


def downgrade() -> None:
    op.drop_index('ix_telegram_link_tokens_telegram_id', table_name='telegram_link_tokens')
    op.drop_index('ix_telegram_link_tokens_user_id', table_name='telegram_link_tokens')
    op.drop_index('ix_telegram_link_tokens_token_hash', table_name='telegram_link_tokens')
    op.drop_table('telegram_link_tokens')
