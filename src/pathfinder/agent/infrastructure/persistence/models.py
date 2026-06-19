"""SQLAlchemy models for agent execution tracking."""
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin


class AgentExecutionModel(Base, UUIDMixin):
    """Thin wrapper matching migration 001 agent_executions table exactly."""
    __tablename__ = "agent_executions"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[UUID] = mapped_column(PGUUID, nullable=False, index=True)
    call_id: Mapped[UUID] = mapped_column(PGUUID, unique=True)
    parent_call_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, default="supervisor")
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, default="execute")
    input_context: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    output_summary: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    tools_called: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    llm_provider: Mapped[str] = mapped_column(String(20), default="deepseek")
    tokens_used: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate: Mapped[float | None] = mapped_column(sa.Numeric(10, 6), nullable=True)
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.text("false"))
    error_message: Mapped[str] = mapped_column(Text, default="")
    error_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    retry_count: Mapped[int] = mapped_column(sa.SmallInteger(), default=0, server_default="0")
    user_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user_modified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=sa.text("NOW()"))


class ApprovalRequestModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_requests"

    execution_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("agent_executions.id"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(50))
    action_summary: Mapped[str] = mapped_column(Text)
    action_detail: Mapped[str] = mapped_column(Text)
    diff_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(10), default="low")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    edits: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
