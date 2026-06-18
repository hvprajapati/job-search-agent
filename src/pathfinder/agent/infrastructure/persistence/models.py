"""SQLAlchemy models for agent execution tracking."""
from uuid import UUID
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin


class AgentExecutionModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_executions"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[UUID] = mapped_column(PGUUID, nullable=False, index=True)
    call_id: Mapped[UUID] = mapped_column(PGUUID, unique=True)
    parent_call_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, default="supervisor")
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, default="execute")
    intent: Mapped[str] = mapped_column(String(50), default="")
    intent_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    user_message: Mapped[str] = mapped_column(Text, default="")
    execution_plan: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    tool_results: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    final_response: Mapped[str] = mapped_column(Text, default="")
    llm_model: Mapped[str] = mapped_column(String(50), default="")
    llm_provider: Mapped[str] = mapped_column(String(20), default="deepseek")
    tokens_used: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    is_success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str] = mapped_column(Text, default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
