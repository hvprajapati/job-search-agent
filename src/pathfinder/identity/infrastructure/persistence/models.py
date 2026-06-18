"""SQLAlchemy ORM models for identity domain."""
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pathfinder.shared.infrastructure.persistence.base import Base, UUIDMixin, TimestampMixin
from pathfinder.identity.domain.entities import User
from pathfinder.identity.domain.value_objects import Email, Tier, UserStatus, UserRole


class TenantModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    plan: Mapped[str] = mapped_column(String(20), default="free")
    status: Mapped[str] = mapped_column(String(20), default="active")
    billing_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    max_users: Mapped[int | None] = mapped_column(nullable=True)
    storage_limit_bytes: Mapped[int | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("idx_users_tenant_email", "tenant_id", "email"),
        Index("idx_users_oauth", "oauth_provider", "oauth_subject",
              unique=True, postgresql_where="oauth_provider IS NOT NULL"),
    )

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[str] = mapped_column(String(20), default="free")
    status: Mapped[str] = mapped_column(String(20), default="active")
    role: Mapped[str] = mapped_column(String(20), default="user")
    locale: Mapped[str] = mapped_column(String(10), default="en-US")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_domain(self) -> User:
        return User(
            id=self.id,
            email=Email(value=self.email),
            hashed_password=self.hashed_password,
            full_name=self.full_name,
            tier=Tier(self.tier),
            status=UserStatus(self.status),
            role=UserRole(self.role),
            email_verified=self.email_verified,
            oauth_provider=self.oauth_provider,
            oauth_subject=self.oauth_subject,
            avatar_url=self.avatar_url,
            locale=self.locale,
            timezone=self.timezone,
            last_login_at=self.last_login_at,
            deleted_at=self.deleted_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, user: User) -> "UserModel":
        return cls(
            id=user.id,
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            email=user.email.value,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            tier=user.tier.value,
            status=user.status.value,
            role=user.role.value,
            email_verified=user.email_verified,
            oauth_provider=user.oauth_provider,
            oauth_subject=user.oauth_subject,
            avatar_url=user.avatar_url,
            locale=user.locale,
            timezone=user.timezone,
            last_login_at=user.last_login_at,
            deleted_at=user.deleted_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
