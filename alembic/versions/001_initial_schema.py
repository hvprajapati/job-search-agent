"""001_initial_schema — core tables.

Revision ID: 001
Create Date: 2026-06-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── Identity ──
    op.create_table("tenants",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("billing_email", sa.String(320)),
        sa.Column("settings", JSONB(), server_default="{}"),
        sa.Column("max_users", sa.Integer()),
        sa.Column("storage_limit_bytes", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table("users",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("hashed_password", sa.String(255)),
        sa.Column("oauth_provider", sa.String(50)),
        sa.Column("oauth_subject", sa.String(255)),
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("locale", sa.String(10), server_default="en-US"),
        sa.Column("timezone", sa.String(50), server_default="UTC"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("idx_users_tenant_email", "users", ["tenant_id", "email"])
    op.create_index("idx_users_oauth", "users", ["oauth_provider", "oauth_subject"],
                    unique=True, postgresql_where=sa.text("oauth_provider IS NOT NULL"))

    op.create_table("sessions",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("token_family_id", UUID(), nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_sessions_user", "sessions", ["user_id", "is_revoked"])
    op.create_index("idx_sessions_expiry", "sessions", ["expires_at"],
                    postgresql_where=sa.text("is_revoked = false"))
    op.create_index("idx_sessions_family", "sessions", ["token_family_id"])

    # ── Profile ──
    op.create_table("profiles",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("structured_data", JSONB(), nullable=False, server_default="{}"),
        sa.Column("embedding", Vector(3072)),
        sa.Column("summary", sa.Text()),
        sa.Column("parsing_confidence", JSONB(), server_default="{}"),
        sa.Column("enrichment_data", JSONB(), server_default="{}"),
        sa.Column("source", sa.ARRAY(sa.Text())),
        sa.Column("full_name_snapshot", sa.String(255)),
        sa.Column("headline_snapshot", sa.String(255)),
        sa.Column("skill_names_snapshot", sa.ARRAY(sa.String())),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("resumes",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("template_id", sa.String(50), nullable=False, server_default="base"),
        sa.Column("content", JSONB(), nullable=False, server_default="{}"),
        sa.Column("file_url", sa.Text()),
        sa.Column("file_format", sa.String(10), server_default="pdf"),
        sa.Column("is_base", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("tailored_for_job_id", UUID(), nullable=True),
        sa.Column("tailored_for_role", sa.String(255)),
        sa.Column("performance_metrics", JSONB(), server_default="{}"),
        sa.Column("ats_parse_score", sa.SmallInteger()),
        sa.Column("versions", JSONB(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("cover_letters",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(50), server_default="professional"),
        sa.Column("company_research", JSONB(), server_default="{}"),
        sa.Column("factuality_score", sa.Float()),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── Jobs ──
    op.create_table("companies",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False, unique=True),
        sa.Column("website", sa.Text()),
        sa.Column("industry", sa.String(100)),
        sa.Column("industry_tags", sa.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("size_range", sa.String(20)),
        sa.Column("employee_count", sa.Integer()),
        sa.Column("funding_stage", sa.String(50)),
        sa.Column("total_funding", sa.BigInteger()),
        sa.Column("founded_year", sa.SmallInteger()),
        sa.Column("headquarters", JSONB(), server_default="{}"),
        sa.Column("tech_stack", JSONB(), server_default="{}"),
        sa.Column("culture_tags", JSONB(), server_default="{}"),
        sa.Column("glassdoor_rating", sa.Float()),
        sa.Column("career_page_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table("job_postings",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_job_id", sa.String(64), nullable=False, unique=True),
        sa.Column("company_id", UUID(), sa.ForeignKey("companies.id")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("normalized_title", sa.String(255)),
        sa.Column("location", JSONB(), server_default="{}"),
        sa.Column("remote_policy", sa.String(20)),
        sa.Column("description_raw", sa.Text()),
        sa.Column("description_clean", sa.Text()),
        sa.Column("description_summary", sa.Text()),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(50)),
        sa.Column("application_url", sa.Text()),
        sa.Column("job_embedding", Vector(3072)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("refreshed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("tech_stack", sa.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("salary_min", sa.Float()),
        sa.Column("salary_max", sa.Float()),
        sa.Column("salary_currency", sa.String(3), server_default="USD"),
        sa.Column("seniority", sa.String(30), server_default="unspecified"),
        sa.Column("source_ids", JSONB(), server_default="{}"),
        sa.Column("source_urls", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_jobs_active_fresh", "job_postings", ["is_active", "first_seen_at"])
    op.create_index("idx_jobs_company", "job_postings", ["company_id"])

    op.create_table("job_sources",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("base_url", sa.Text()),
        sa.Column("scraper_config", JSONB(), nullable=False, server_default="{}"),
        sa.Column("priority", sa.SmallInteger(), server_default="5"),
        sa.Column("sweep_interval_min", sa.Integer(), server_default="60"),
        sa.Column("health_status", sa.String(20), server_default="healthy"),
        sa.Column("last_sweep_at", sa.DateTime(timezone=True)),
        sa.Column("last_sweep_status", sa.String(20)),
        sa.Column("success_rate", sa.Float()),
        sa.Column("jobs_per_sweep_avg", sa.Float()),
        sa.Column("consecutive_fails", sa.SmallInteger(), server_default="0"),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── Tracking ──
    op.create_table("applications",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", UUID(), sa.ForeignKey("job_postings.id")),
        sa.Column("resume_id", UUID(), sa.ForeignKey("resumes.id")),
        sa.Column("cover_letter_id", UUID(), sa.ForeignKey("cover_letters.id")),
        sa.Column("status", sa.String(30), nullable=False, server_default="saved"),
        sa.Column("status_history", JSONB(), server_default="[]"),
        sa.Column("source_channel", sa.String(50)),
        sa.Column("match_score_at_apply", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True)),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )
    op.create_index("idx_applications_user_status", "applications", ["user_id", "status"])

    # ── Agent & Audit ──
    op.create_table("agent_executions",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", UUID(), nullable=False),
        sa.Column("call_id", UUID(), nullable=False, unique=True),
        sa.Column("parent_call_id", UUID()),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("input_context", JSONB(), server_default="{}"),
        sa.Column("output_summary", JSONB(), server_default="{}"),
        sa.Column("tools_called", JSONB(), server_default="[]"),
        sa.Column("llm_model", sa.String(50), nullable=False),
        sa.Column("llm_provider", sa.String(20)),
        sa.Column("tokens_used", JSONB(), server_default="{}"),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("cost_estimate", sa.Numeric(10, 6)),
        sa.Column("is_success", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text()),
        sa.Column("error_type", sa.String(50)),
        sa.Column("retry_count", sa.SmallInteger(), server_default="0"),
        sa.Column("user_approved", sa.Boolean()),
        sa.Column("user_modified", sa.Boolean()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_agent_user_time", "agent_executions", ["user_id", sa.text("created_at DESC")])
    op.create_index("idx_agent_session", "agent_executions", ["session_id"])

    op.create_table("audit_logs",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("actor_id", UUID()),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("action_category", sa.String(50)),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", UUID()),
        sa.Column("changes", JSONB(), server_default="{}"),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("request_id", UUID()),
        sa.Column("metadata", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", "created_at"),
    )
    op.create_index("idx_audit_user_time", "audit_logs", ["user_id", sa.text("created_at DESC")])

    # ── Memory ──
    op.create_table("episodic_memories",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", UUID(), nullable=False),
        sa.Column("episode_type", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(50), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False, server_default="{}"),
        sa.Column("importance_score", sa.Float(), server_default="0.5"),
        sa.Column("emotion_signal", sa.Float()),
        sa.Column("embedding", Vector(1536)),
        sa.Column("context_summary", sa.Text()),
        sa.Column("parent_episode_id", UUID()),
        sa.Column("consolidation_id", UUID()),
        sa.Column("is_consolidated", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", "created_at"),
    )
    op.create_index("idx_episodic_user_time", "episodic_memories", ["user_id", sa.text("created_at DESC")])

    op.create_table("semantic_memories",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("content", JSONB(), nullable=False, server_default="{}"),
        sa.Column("content_text", sa.Text()),
        sa.Column("embedding", Vector(3072)),
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("evidence_episodes", sa.ARRAY(UUID()), server_default="{}"),
        sa.Column("evidence_count", sa.Integer(), server_default="1"),
        sa.Column("importance", sa.Float(), server_default="0.5"),
        sa.Column("access_count", sa.Integer(), server_default="0"),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True)),
        sa.Column("last_updated_at", sa.DateTime(timezone=True)),
        sa.Column("consolidation_run_id", UUID()),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_semantic_user_type", "semantic_memories", ["user_id", "memory_type"])

    op.create_table("procedural_memories",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pattern_type", sa.String(50)),
        sa.Column("context_signature", sa.Text()),
        sa.Column("context_embedding", Vector(1536)),
        sa.Column("action_sequence", JSONB(), server_default="{}"),
        sa.Column("success_rate", sa.Float(), server_default="0.0"),
        sa.Column("execution_count", sa.Integer(), server_default="0"),
        sa.Column("avg_latency_ms", sa.Integer(), server_default="0"),
        sa.Column("last_executed_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_proc_user_active", "procedural_memories", ["user_id", "is_active"])

    # ── Knowledge ──
    op.create_table("knowledge_documents",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(50)),
        sa.Column("source_id", sa.String(255)),
        sa.Column("title", sa.String(500)),
        sa.Column("content_raw", sa.Text()),
        sa.Column("content_clean", sa.Text()),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("embedding_model", sa.String(50), server_default="deepseek-embed"),
        sa.Column("is_indexed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_kdoc_user_source", "knowledge_documents", ["user_id", "source_type", "source_id"])

    op.create_table("knowledge_chunks",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("content_hash", sa.String(32)),
        sa.Column("embedding", Vector(3072)),
        sa.Column("metadata", JSONB(), server_default="{}"),
        sa.Column("chunk_index", sa.Integer(), server_default="0"),
        sa.Column("token_count", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_kchunk_user", "knowledge_chunks", ["user_id"])
    op.create_index("idx_kchunk_document", "knowledge_chunks", ["document_id"])

    # ── HNSW indexes ──
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_embedding ON episodic_memories "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 12, ef_construction = 150)"
    )
    # NOTE: 3072d HNSW indexes (jobs, semantic, knowledge) deferred to V1
    # Current pgvector version limits HNSW to 2000 dimensions.
    # Sequential scan is acceptable until embeddings are populated.


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("procedural_memories")
    op.drop_table("semantic_memories")
    op.drop_table("episodic_memories")
    op.drop_table("audit_logs")
    op.drop_table("agent_executions")
    op.drop_table("applications")
    op.drop_table("job_sources")
    op.drop_table("job_postings")
    op.drop_table("companies")
    op.drop_table("cover_letters")
    op.drop_table("resumes")
    op.drop_table("profiles")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("tenants")
