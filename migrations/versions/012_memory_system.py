"""Add structured long-term memory and privacy controls."""
from alembic import op
import sqlalchemy as sa


revision = '012_memory_system'
down_revision = '011_reaction_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'messages',
        sa.Column('memory_visibility', sa.String(length=20), server_default='normal', nullable=False),
    )
    op.add_column('messages', sa.Column('memory_processed_at', sa.DateTime(), nullable=True))
    op.create_index('ix_messages_memory_processed_at', 'messages', ['memory_processed_at'])

    op.create_table(
        'memory_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('kind', sa.String(length=30), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('predicate', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('canonical_key', sa.String(length=40), nullable=False),
        sa.Column('value_hash', sa.String(length=40), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('stability', sa.String(length=20), nullable=False),
        sa.Column('sensitivity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('source_message_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'canonical_key', 'value_hash', name='uq_memory_items_user_key_value'),
    )
    op.create_index('ix_memory_items_user_id', 'memory_items', ['user_id'])
    op.create_index('ix_memory_items_status', 'memory_items', ['status'])
    op.create_index('ix_memory_items_source_message_id', 'memory_items', ['source_message_id'])
    op.create_index('ix_memory_items_user_status', 'memory_items', ['user_id', 'status'])
    op.create_index('ix_memory_items_user_canonical_key', 'memory_items', ['user_id', 'canonical_key'])

    op.create_table(
        'memory_episodes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.UUID(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('people', sa.JSON(), nullable=False),
        sa.Column('topics', sa.JSON(), nullable=False),
        sa.Column('emotional_tone', sa.JSON(), nullable=False),
        sa.Column('unresolved_threads', sa.JSON(), nullable=False),
        sa.Column('retrieval_anchors', sa.JSON(), nullable=False),
        sa.Column('sensitivity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('source_message_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_memory_episodes_user_id', 'memory_episodes', ['user_id'])
    op.create_index('ix_memory_episodes_chat_id', 'memory_episodes', ['chat_id'])
    op.create_index('ix_memory_episodes_status', 'memory_episodes', ['status'])
    op.create_index('ix_memory_episodes_source_message_id', 'memory_episodes', ['source_message_id'])
    op.create_index('ix_memory_episodes_user_status', 'memory_episodes', ['user_id', 'status'])
    op.create_index('ix_memory_episodes_chat_created_at', 'memory_episodes', ['chat_id', 'created_at'])

    op.create_table(
        'memory_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('when_at', sa.DateTime(), nullable=True),
        sa.Column('participants', sa.JSON(), nullable=False),
        sa.Column('kind', sa.String(length=30), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('should_follow_up', sa.Boolean(), nullable=False),
        sa.Column('follow_up_at', sa.DateTime(), nullable=True),
        sa.Column('followed_up_at', sa.DateTime(), nullable=True),
        sa.Column('sensitivity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('source_fragment', sa.Text(), nullable=False),
        sa.Column('source_message_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_memory_events_user_id', 'memory_events', ['user_id'])
    op.create_index('ix_memory_events_chat_id', 'memory_events', ['chat_id'])
    op.create_index('ix_memory_events_when_at', 'memory_events', ['when_at'])
    op.create_index('ix_memory_events_follow_up_at', 'memory_events', ['follow_up_at'])
    op.create_index('ix_memory_events_status', 'memory_events', ['status'])
    op.create_index('ix_memory_events_source_message_id', 'memory_events', ['source_message_id'])
    op.create_index('ix_memory_events_user_status', 'memory_events', ['user_id', 'status'])
    op.create_index('ix_memory_events_follow_up', 'memory_events', ['follow_up_at', 'status'])

    op.create_table(
        'memory_suppressions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('scope', sa.String(length=30), nullable=False),
        sa.Column('target_text', sa.Text(), nullable=False),
        sa.Column('person_name', sa.String(length=255), nullable=True),
        sa.Column('event_title', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_memory_suppressions_user_id', 'memory_suppressions', ['user_id'])
    op.create_index('ix_memory_suppressions_user_created_at', 'memory_suppressions', ['user_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_memory_suppressions_user_created_at', table_name='memory_suppressions')
    op.drop_index('ix_memory_suppressions_user_id', table_name='memory_suppressions')
    op.drop_table('memory_suppressions')

    op.drop_index('ix_memory_events_follow_up', table_name='memory_events')
    op.drop_index('ix_memory_events_user_status', table_name='memory_events')
    op.drop_index('ix_memory_events_source_message_id', table_name='memory_events')
    op.drop_index('ix_memory_events_status', table_name='memory_events')
    op.drop_index('ix_memory_events_follow_up_at', table_name='memory_events')
    op.drop_index('ix_memory_events_when_at', table_name='memory_events')
    op.drop_index('ix_memory_events_chat_id', table_name='memory_events')
    op.drop_index('ix_memory_events_user_id', table_name='memory_events')
    op.drop_table('memory_events')

    op.drop_index('ix_memory_episodes_chat_created_at', table_name='memory_episodes')
    op.drop_index('ix_memory_episodes_user_status', table_name='memory_episodes')
    op.drop_index('ix_memory_episodes_source_message_id', table_name='memory_episodes')
    op.drop_index('ix_memory_episodes_status', table_name='memory_episodes')
    op.drop_index('ix_memory_episodes_chat_id', table_name='memory_episodes')
    op.drop_index('ix_memory_episodes_user_id', table_name='memory_episodes')
    op.drop_table('memory_episodes')

    op.drop_index('ix_memory_items_user_canonical_key', table_name='memory_items')
    op.drop_index('ix_memory_items_user_status', table_name='memory_items')
    op.drop_index('ix_memory_items_source_message_id', table_name='memory_items')
    op.drop_index('ix_memory_items_status', table_name='memory_items')
    op.drop_index('ix_memory_items_user_id', table_name='memory_items')
    op.drop_table('memory_items')

    op.drop_index('ix_messages_memory_processed_at', table_name='messages')
    op.drop_column('messages', 'memory_processed_at')
    op.drop_column('messages', 'memory_visibility')
