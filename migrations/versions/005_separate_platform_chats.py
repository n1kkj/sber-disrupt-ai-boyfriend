"""Separate web and Telegram chats and mark Telegram-only users."""
from alembic import op
import sqlalchemy as sa


revision = '005_separate_platform_chats'
down_revision = '004_scheduled_messages'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_telegram_only', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute(
        sa.text(
            "UPDATE users SET is_telegram_only = TRUE "
            "WHERE email LIKE 'telegram_%@local.invalid'"
        )
    )
    op.add_column('chats', sa.Column('platform', sa.String(length=20), nullable=False, server_default='web'))
    op.execute(sa.text("UPDATE chats SET platform = 'telegram' WHERE title = 'Telegram chat'"))
    op.execute(
        sa.text(
            "WITH ranked_chats AS ("
            " SELECT id, user_id, platform, "
            " first_value(id) OVER (PARTITION BY user_id, platform ORDER BY created_at, id) AS keep_id, "
            " row_number() OVER (PARTITION BY user_id, platform ORDER BY created_at, id) AS row_number "
            " FROM chats"
            ") "
            "UPDATE messages AS messages "
            "SET chat_id = ranked_chats.keep_id "
            "FROM ranked_chats "
            "WHERE messages.chat_id = ranked_chats.id "
            "AND ranked_chats.row_number > 1"
        )
    )
    op.execute(
        sa.text(
            "WITH ranked_chats AS ("
            " SELECT id, row_number() OVER (PARTITION BY user_id, platform ORDER BY created_at, id) AS row_number "
            " FROM chats"
            ") "
            "DELETE FROM chats AS chats "
            "USING ranked_chats "
            "WHERE chats.id = ranked_chats.id "
            "AND ranked_chats.row_number > 1"
        )
    )
    op.create_index('ix_chats_platform', 'chats', ['platform'])
    op.create_index('uq_chats_user_platform', 'chats', ['user_id', 'platform'], unique=True)


def downgrade() -> None:
    op.drop_index('uq_chats_user_platform', table_name='chats')
    op.drop_index('ix_chats_platform', table_name='chats')
    op.drop_column('chats', 'platform')
    op.drop_column('users', 'is_telegram_only')
