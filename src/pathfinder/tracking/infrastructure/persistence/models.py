"""SQLAlchemy ORM model for applications."""
from uuid import UUID
from sqlalchemy import String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.tracking.domain.entities import Application


class ApplicationModel(Base, UUIDMixin):
    """Thin wrapper matching migration 001 applications table exactly."""
    __tablename__ = "applications"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[UUID] = mapped_column(PGUUID, ForeignKey("job_postings.id"), nullable=False)
    resume_id: Mapped[UUID | None] = mapped_column(PGUUID, ForeignKey("resumes.id"), nullable=True)
    cover_letter_id: Mapped[UUID | None] = mapped_column(PGUUID, nullable=True)  # FK omitted: cover_letters table descoped
    status: Mapped[str] = mapped_column(String(30), default="saved")
    status_history: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    source_channel: Mapped[str] = mapped_column(String(50), default="")
    match_score_at_apply: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # Unique: one application per user per job
    )

    def to_domain(self) -> Application:
        return Application(
            id=self.id, user_id=self.user_id, job_id=self.job_id,
            resume_id=self.resume_id, cover_letter_id=None,  # descoped
            status=self.status, status_history=self.status_history or [],
            source_channel=self.source_channel or "",
            match_score=self.match_score_at_apply,
            notes=self.notes or "",
            applied_at=self.applied_at,
            next_follow_up_at=self.next_follow_up_at,
            is_archived=self.is_archived or False,
            created_at=self.created_at, updated_at=self.last_updated_at,
        )

    @classmethod
    def from_domain(cls, app: Application) -> "ApplicationModel":
        return cls(
            id=app.id, user_id=app.user_id, job_id=app.job_id,
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            resume_id=app.resume_id, cover_letter_id=None,  # descoped
            status=app.status, status_history=app.status_history,
            source_channel=app.source_channel,
            match_score_at_apply=app.match_score,
            notes=app.notes, applied_at=app.applied_at,
            next_follow_up_at=app.next_follow_up_at,
            is_archived=app.is_archived,
            created_at=app.created_at, last_updated_at=app.updated_at,
        )
