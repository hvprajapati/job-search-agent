"""SQLAlchemy models for memory domain — thin wrappers for tables in migration 001."""
from uuid import UUID
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin


class EpisodicMemoryModel(Base, UUIDMixin):
    __tablename__ = "episodic_memories"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"))
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    episode_type: Mapped[str] = mapped_column(String(50))
    actor: Mapped[str] = mapped_column(String(50), default="system")
    action: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    importance_score: Mapped[float] = mapped_column(Float, default=0.3)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    context_summary: Mapped[str | None] = mapped_column(Text)
    parent_episode_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    consolidation_run_id: Mapped[UUID | None] = mapped_column("consolidation_id", PGUUID, nullable=True)
    is_consolidated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SemanticMemoryModel(Base, UUIDMixin):
    # NOTE: TimestampMixin not used — this table has last_updated_at (not updated_at)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_updated_at: Mapped[datetime | None] = mapped_column("last_updated_at", DateTime(timezone=True), nullable=True)
    __tablename__ = "semantic_memories"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"))
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    memory_type: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(Text)
    content: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    content_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_episodes: Mapped[list | None] = mapped_column(ARRAY(PGUUID), server_default="{}")
    evidence_count: Mapped[int] = mapped_column(Integer, default=1)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consolidation_run_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
