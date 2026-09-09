"""Add onboarding preferences and versioned companion prompts."""
from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = '006_onboarding_character'
down_revision = '005_separate_platform_chats'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'character_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('boyfriend_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('display_name', sa.String(length=120), nullable=False),
        sa.Column('style', sa.Text(), nullable=False),
        sa.Column('boundaries', sa.Text(), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('role_type', sa.String(length=30), nullable=False, server_default='boyfriend'),
        sa.Column('gender', sa.String(length=30), nullable=False, server_default='male'),
        sa.Column('pronouns', sa.String(length=120), nullable=True),
        sa.Column('voice_profile', sa.String(length=120), nullable=True),
        sa.Column('prompt_version', sa.String(length=80), nullable=False, server_default='v1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['boyfriend_id'], ['boyfriends.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('boyfriend_id', 'version', name='uq_character_versions_boyfriend_version'),
    )
    op.create_index('ix_character_versions_boyfriend_id', 'character_versions', ['boyfriend_id'])
    op.create_index('ix_character_versions_is_active', 'character_versions', ['is_active'])
    op.create_table(
        'user_profiles',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('companion_role', sa.String(length=30), nullable=False, server_default='boyfriend'),
        sa.Column('companion_gender', sa.String(length=30), nullable=False, server_default='male'),
        sa.Column('user_gender', sa.String(length=30), nullable=False, server_default='unspecified'),
        sa.Column('user_pronouns', sa.String(length=120), nullable=True),
        sa.Column('preferred_address', sa.String(length=120), nullable=True),
        sa.Column('language', sa.String(length=12), nullable=False, server_default='ru'),
        sa.Column('timezone', sa.String(length=64), nullable=False, server_default='Europe/Moscow'),
        sa.Column('quiet_hours_start', sa.Time(), nullable=True),
        sa.Column('quiet_hours_end', sa.Time(), nullable=True),
        sa.Column('proactive_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('daily_proactive_limit', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_table(
        'onboarding_states',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='in_progress'),
        sa.Column('step', sa.String(length=50), nullable=False, server_default='companion_gender'),
        sa.Column('answers', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    bind = op.get_bind()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    boyfriends = bind.execute(sa.text('SELECT id, name, system_prompt FROM boyfriends')).mappings().all()
    for boyfriend in boyfriends:
        exists = bind.execute(
            sa.text('SELECT 1 FROM character_versions WHERE boyfriend_id = :boyfriend_id LIMIT 1'),
            {'boyfriend_id': boyfriend['id']},
        ).scalar_one_or_none()
        if exists is None:
            bind.execute(
                sa.text(
                    'INSERT INTO character_versions '
                    '(id, boyfriend_id, version, display_name, style, boundaries, system_prompt, '
                    'role_type, gender, pronouns, prompt_version, is_active, created_at) '
                    'VALUES (:id, :boyfriend_id, 1, :display_name, :style, :boundaries, :system_prompt, '
                    ':role_type, :gender, :pronouns, :prompt_version, TRUE, :created_at)'
                ),
                {
                    'id': str(uuid4()),
                    'boyfriend_id': boyfriend['id'],
                    'display_name': boyfriend['name'],
                    'style': 'Теплый, внимательный, живой и уважительный стиль общения.',
                    'boundaries': 'Не выдавай себя за реального человека и уважай границы пользователя.',
                    'system_prompt': boyfriend['system_prompt'],
                    'role_type': 'boyfriend',
                    'gender': 'male',
                    'pronouns': 'он/его',
                    'prompt_version': 'v1',
                    'created_at': now,
                },
            )
    users = bind.execute(sa.text('SELECT id FROM users')).scalars().all()
    for user_id in users:
        bind.execute(
            sa.text(
                'INSERT INTO user_profiles (user_id, created_at, updated_at) '
                'VALUES (:user_id, :created_at, :updated_at) ON CONFLICT (user_id) DO NOTHING'
            ),
            {'user_id': user_id, 'created_at': now, 'updated_at': now},
        )
        bind.execute(
            sa.text(
                'INSERT INTO onboarding_states (user_id, created_at, updated_at) '
                'VALUES (:user_id, :created_at, :updated_at) ON CONFLICT (user_id) DO NOTHING'
            ),
            {'user_id': user_id, 'created_at': now, 'updated_at': now},
        )


def downgrade() -> None:
    op.drop_table('onboarding_states')
    op.drop_table('user_profiles')
    op.drop_index('ix_character_versions_is_active', table_name='character_versions')
    op.drop_index('ix_character_versions_boyfriend_id', table_name='character_versions')
    op.drop_table('character_versions')
