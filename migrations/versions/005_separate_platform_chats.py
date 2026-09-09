"""Separate web and Telegram chats and mark Telegram-only users."""
from datetime import datetime, timezone
from uuid import uuid4

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
    bind = op.get_bind()
    active_boyfriend = bind.execute(
        sa.text(
            "SELECT id FROM boyfriends "
            "WHERE is_active = TRUE ORDER BY created_at LIMIT 1"
        )
    ).scalar_one_or_none()
    if active_boyfriend is not None:
        linked_users = bind.execute(
            sa.text(
                "SELECT id FROM users "
                "WHERE telegram_id IS NOT NULL AND is_telegram_only = FALSE"
            )
        ).scalars().all()
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        for user_id in linked_users:
            for platform, title in (('web', 'Web chat'), ('telegram', 'Telegram chat')):
                chat_exists = bind.execute(
                    sa.text(
                        "SELECT 1 FROM chats "
                        "WHERE user_id = :user_id AND platform = :platform LIMIT 1"
                    ),
                    {'user_id': user_id, 'platform': platform},
                ).scalar_one_or_none()
                if chat_exists is not None:
                    continue
                bind.execute(
                    sa.text(
                        "INSERT INTO chats "
                        "(id, user_id, boyfriend_id, title, platform, created_at, updated_at) "
                        "VALUES (:id, :user_id, :boyfriend_id, :title, :platform, :created_at, :updated_at)"
                    ),
                    {
                        'id': str(uuid4()),
                        'user_id': user_id,
                        'boyfriend_id': active_boyfriend,
                        'title': title,
                        'platform': platform,
                        'created_at': created_at,
                        'updated_at': created_at,
                    },
                )
    op.create_index('ix_chats_platform', 'chats', ['platform'])
    op.create_index('uq_chats_user_platform', 'chats', ['user_id', 'platform'], unique=True)


def downgrade() -> None:
    op.drop_index('uq_chats_user_platform', table_name='chats')
    op.drop_index('ix_chats_platform', table_name='chats')
    op.drop_column('chats', 'platform')
    op.drop_column('users', 'is_telegram_only')
