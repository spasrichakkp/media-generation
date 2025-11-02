"""Initial schema with users, generation_jobs, and generated_content tables

Revision ID: 001
Revises: 
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('api_key_hash', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('quota_limit', sa.Integer(), nullable=True),
        sa.Column('quota_used', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('quota_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_api_key_hash'), 'users', ['api_key_hash'], unique=False)

    # Create generation_jobs table
    op.create_table(
        'generation_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('priority', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('webhook_url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generation_jobs_id'), 'generation_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_generation_jobs_user_id'), 'generation_jobs', ['user_id'], unique=False)
    op.create_index(op.f('ix_generation_jobs_content_type'), 'generation_jobs', ['content_type'], unique=False)
    op.create_index(op.f('ix_generation_jobs_status'), 'generation_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_generation_jobs_priority'), 'generation_jobs', ['priority'], unique=False)
    op.create_index(op.f('ix_generation_jobs_created_at'), 'generation_jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_generation_jobs_completed_at'), 'generation_jobs', ['completed_at'], unique=False)
    
    # Composite indexes for common queries
    op.create_index('ix_jobs_user_status', 'generation_jobs', ['user_id', 'status'], unique=False)
    op.create_index('ix_jobs_status_priority', 'generation_jobs', ['status', 'priority', 'created_at'], unique=False)
    op.create_index('ix_jobs_created_at_status', 'generation_jobs', ['created_at', 'status'], unique=False)

    # Create generated_content table
    op.create_table(
        'generated_content',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_url', sa.String(length=1000), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_format', sa.String(length=50), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('content_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('nsfw_score', sa.Float(), nullable=True),
        sa.Column('is_moderated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['job_id'], ['generation_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )
    op.create_index(op.f('ix_generated_content_id'), 'generated_content', ['id'], unique=False)
    op.create_index(op.f('ix_generated_content_job_id'), 'generated_content', ['job_id'], unique=True)
    op.create_index(op.f('ix_generated_content_content_type'), 'generated_content', ['content_type'], unique=False)
    op.create_index(op.f('ix_generated_content_created_at'), 'generated_content', ['created_at'], unique=False)
    op.create_index(op.f('ix_generated_content_is_public'), 'generated_content', ['is_public'], unique=False)
    op.create_index(op.f('ix_generated_content_is_moderated'), 'generated_content', ['is_moderated'], unique=False)
    
    # Composite indexes for common queries
    op.create_index('ix_content_type_public', 'generated_content', ['content_type', 'is_public'], unique=False)
    op.create_index('ix_content_nsfw', 'generated_content', ['nsfw_score'], unique=False)
    op.create_index('ix_content_moderated', 'generated_content', ['is_moderated'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index('ix_content_moderated', table_name='generated_content')
    op.drop_index('ix_content_nsfw', table_name='generated_content')
    op.drop_index('ix_content_type_public', table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_is_moderated'), table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_is_public'), table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_created_at'), table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_content_type'), table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_job_id'), table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_id'), table_name='generated_content')
    op.drop_table('generated_content')
    
    op.drop_index('ix_jobs_created_at_status', table_name='generation_jobs')
    op.drop_index('ix_jobs_status_priority', table_name='generation_jobs')
    op.drop_index('ix_jobs_user_status', table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_completed_at'), table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_created_at'), table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_priority'), table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_status'), table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_content_type'), table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_user_id'), table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_id'), table_name='generation_jobs')
    op.drop_table('generation_jobs')
    
    op.drop_index(op.f('ix_users_api_key_hash'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')

