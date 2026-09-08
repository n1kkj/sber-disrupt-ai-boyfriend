"""Add scheduled execution time to messages."""
from alembic import op
import sqlalchemy as sa


revision = '004_scheduled_messages'
down_revision = '003_message_flow'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('messages', sa.Column('scheduled_at', sa.DateTime(), nullable=True))
    op.create_index('ix_messages_scheduled_at', 'messages', ['scheduled_at'])


def downgrade() -> None:
    op.drop_index('ix_messages_scheduled_at', table_name='messages')
    op.drop_column('messages', 'scheduled_at')
