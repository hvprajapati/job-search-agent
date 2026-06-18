"""Default tenant management — removes hardcoded UUIDs."""
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


def get_default_tenant_id() -> UUID:
    """Return the default tenant UUID. In MVP, all individual users share one tenant."""
    return DEFAULT_TENANT_ID


async def ensure_default_tenant_exists():
    """Create the default tenant if it doesn't exist."""
    from pathfinder.shared.infrastructure.database import get_sessionmaker
    from sqlalchemy import text
    maker = get_sessionmaker()
    async with maker() as session:
        result = await session.execute(
            text("SELECT id FROM tenants WHERE id = :id"),
            {"id": DEFAULT_TENANT_ID},
        )
        if result.scalar_one_or_none() is None:
            await session.execute(
                text("INSERT INTO tenants (id, name, slug, plan, status) VALUES (:id, 'Default', 'default', 'free', 'active')"),
                {"id": DEFAULT_TENANT_ID},
            )
            await session.commit()
            logger.info("Default tenant created")
