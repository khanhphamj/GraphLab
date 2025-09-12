"""complete_initial_schema

Revision ID: 59c11d2dee44
Revises: 
Create Date: 2025-09-12 04:xx:xx.xxxxxx

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '59c11d2dee44'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # ========== PHASE 1: Create base tables without circular foreign keys ==========
    
    # 1. Create users table (no dependencies)
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('profile', sa.JSON(), nullable=True),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Create labs table (only with owner_id, no active_connection_id/active_schema_id yet)
    op.create_table('labs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('research_domain', sa.String(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('active', 'archived', 'suspended', name='lab_status'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create kg_schemas table
    op.create_table('kg_schemas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('schema_definition', sa.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('version > 0', name='ck_kg_schemas_version_positive'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lab_id', 'version', name='uq_kg_schemas_lab_version')
    )

    # 4. Create neo4j_connections table (without schema_id initially)
    op.create_table('neo4j_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connection_name', sa.String(), nullable=False),
        sa.Column('uri', sa.String(), nullable=False),
        sa.Column('database_name', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('secret_id', sa.String(), nullable=False),
        sa.Column('namespace', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lab_id', 'connection_name', name='uq_neo4j_connections_lab_name')
    )

    # 5. Create research_papers table
    op.create_table('research_papers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('arxiv_id', sa.String(), nullable=True),
        sa.Column('doi', sa.String(), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('authors', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=False),
        sa.Column('pdf_url', sa.Text(), nullable=True),
        sa.Column('neo4j_uuid', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processing_status', sa.Enum('pending', 'processing', 'completed', 'failed', name='paper_processing_status'), nullable=False),
        sa.Column('keywords_matched', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('published_date', sa.Date(), nullable=True),
        sa.Column('crawled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lab_id', 'arxiv_id', name='uq_research_papers_lab_arxiv'),
        sa.UniqueConstraint('lab_id', 'doi', name='uq_research_papers_lab_doi')
    )

    # 6. Create brainstorm_sessions table
    op.create_table('brainstorm_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('active', 'completed', 'archived', name='session_status'), nullable=False),
        sa.Column('session_data', sa.JSON(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. Create research_keywords table
    op.create_table('research_keywords',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term', sa.String(), nullable=False),
        sa.Column('weight', sa.Numeric(), nullable=True),
        sa.Column('source', sa.Enum('user', 'ai', 'imported', name='research_keyword_source'), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['brainstorm_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_research_keywords_session_term', 'research_keywords', ['session_id', sa.text('lower(term)')], unique=True)

    # 8. Create lab_members table
    op.create_table('lab_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', 'viewer', name='lab_member_role'), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lab_id', 'user_id', name='uq_lab_members_lab_user')
    )

    # 9. Create processing_jobs table
    op.create_table('processing_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_type', sa.Enum('paper_crawl', 'paper_process', 'entity_extract', 'vector_embed', 'kg_upsert', 'schema_migrate', 'index_rebuild', 'data_export', name='processing_job_type'), nullable=False),
        sa.Column('status', sa.Enum('queued', 'running', 'completed', 'failed', 'cancelled', name='processing_job_status'), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('queue', sa.String(), nullable=True),
        sa.Column('worker_id', sa.String(), nullable=True),
        sa.Column('input_config', sa.JSON(), nullable=True),
        sa.Column('output_result', sa.JSON(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=True),
        sa.Column('processed_items', sa.Integer(), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=True),
        sa.Column('retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. Create conversations table
    op.create_table('conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 11. Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token_hash', sa.String(), nullable=False),
        sa.Column('refresh_token_hash', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token_hash')
    )

    # 12. Create user_verifications table
    op.create_table('user_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('verification_type', sa.Enum('email_verify', 'password_reset', 'two_factor', name='verification_type'), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )

    # 13. Create user_oauth_accounts table
    op.create_table('user_oauth_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.Enum('google', 'github', 'microsoft', 'facebook', name='oauth_provider'), nullable=False),
        sa.Column('provider_user_id', sa.String(), nullable=False),
        sa.Column('provider_email', sa.String(), nullable=True),
        sa.Column('access_token_id', sa.String(), nullable=True),
        sa.Column('refresh_token_id', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_user_oauth_accounts_provider_user')
    )

    # 14. Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('can_read', sa.Boolean(), nullable=False),
        sa.Column('can_write', sa.Boolean(), nullable=False),
        sa.Column('can_admin', sa.Boolean(), nullable=False),
        sa.Column('lab_access', sa.JSON(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )

    # 15. Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.Enum('login', 'logout', 'register', 'password_change', 'lab_create', 'lab_delete', 'api_key_create', 'data_export', 'schema_change', name='audit_action'), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('json_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 16. Tables that depend on previous tables
    op.create_table('job_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_name', sa.String(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'skipped', name='job_step_status'), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('step_order > 0', name='ck_job_steps_order_positive'),
        sa.ForeignKeyConstraint(['job_id'], ['processing_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', 'step_order', name='uq_job_steps_job_order')
    )

    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', name='message_role'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('parent_message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('paper_analysis',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analysis_type', sa.Enum('keyword_extraction', 'summary_generation', 'entity_recognition', 'classification', name='paper_analysis_type'), nullable=False),
        sa.Column('result_data', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(), nullable=True),
        sa.Column('model_version', sa.String(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['research_papers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # ========== PHASE 2: Add circular foreign key columns ==========
    
    # Add missing columns to labs table
    op.add_column('labs', sa.Column('active_connection_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('labs', sa.Column('active_schema_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add missing column to neo4j_connections table
    op.add_column('neo4j_connections', sa.Column('schema_id', postgresql.UUID(as_uuid=True), nullable=False))

    # ========== PHASE 3: Create circular foreign key constraints ==========
    
    # Create foreign key constraints for the circular references
    op.create_foreign_key('fk_labs_active_connection', 'labs', 'neo4j_connections', ['active_connection_id'], ['id'])
    op.create_foreign_key('fk_labs_active_schema', 'labs', 'kg_schemas', ['active_schema_id'], ['id'])
    op.create_foreign_key('fk_neo4j_connections_schema', 'neo4j_connections', 'kg_schemas', ['schema_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    # Drop in reverse order
    op.drop_table('paper_analysis')
    op.drop_table('messages')
    op.drop_table('job_steps')
    op.drop_table('audit_logs')
    op.drop_table('api_keys')
    op.drop_table('user_oauth_accounts')
    op.drop_table('user_verifications')
    op.drop_table('user_sessions')
    op.drop_table('conversations')
    op.drop_table('processing_jobs')
    op.drop_table('lab_members')
    op.drop_table('research_keywords')
    op.drop_table('brainstorm_sessions')
    op.drop_table('research_papers')
    op.drop_table('neo4j_connections')
    op.drop_table('kg_schemas')
    op.drop_table('labs')
    op.drop_table('users')
