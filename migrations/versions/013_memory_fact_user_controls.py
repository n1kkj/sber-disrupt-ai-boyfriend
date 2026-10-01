"""Add user-facing memory fact deletion controls."""
from alembic import op
import sqlalchemy as sa


revision = '013_memory_fact_user_controls'
down_revision = '012_memory_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('memory_items', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('memory_items', sa.Column('deletion_source', sa.String(length=30), nullable=True))

    op.create_table(
        'memory_fact_deletion_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('memory_item_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['memory_item_id'], ['memory_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_memory_fact_deletion_events_user_id',
        'memory_fact_deletion_events',
        ['user_id'],
    )
    op.create_index(
        'ix_memory_fact_deletion_events_memory_item_id',
        'memory_fact_deletion_events',
        ['memory_item_id'],
    )
    op.create_index(
        'ix_memory_fact_deletion_events_user_created_at',
        'memory_fact_deletion_events',
        ['user_id', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_memory_fact_deletion_events_user_created_at',
        table_name='memory_fact_deletion_events',
    )
    op.drop_index(
        'ix_memory_fact_deletion_events_memory_item_id',
        table_name='memory_fact_deletion_events',
    )
    op.drop_index(
        'ix_memory_fact_deletion_events_user_id',
        table_name='memory_fact_deletion_events',
    )
    op.drop_table('memory_fact_deletion_events')
    op.drop_column('memory_items', 'deletion_source')
    op.drop_column('memory_items', 'deleted_at')
