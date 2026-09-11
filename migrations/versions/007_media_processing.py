"""Add media processing results and metadata."""
from alembic import op
import sqlalchemy as sa


revision = '007_media_processing'
down_revision = '006_onboarding_character'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('media_assets', sa.Column('transcript', sa.Text(), nullable=True))
    op.add_column('media_assets', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('media_assets', sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'))
    op.add_column('media_assets', sa.Column('error_message', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('media_assets', 'error_message')
    op.drop_column('media_assets', 'metadata_json')
    op.drop_column('media_assets', 'description')
    op.drop_column('media_assets', 'transcript')
