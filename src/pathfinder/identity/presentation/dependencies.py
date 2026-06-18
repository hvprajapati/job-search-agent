"""FastAPI dependency wiring for identity."""
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.domain.entities import User
from pathfinder.identity.infrastructure.persistence.user_repository import SqlUserRepository
from pathfinder.identity.infrastructure.auth.jwt_service import JWTService
from pathfinder.shared.domain.exceptions import UnauthorizedError


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header")

    token = auth_header[7:]
    jwt_svc = JWTService()
    try:
        claims = jwt_svc.decode(token)
    except Exception:
        raise UnauthorizedError("Invalid or expired token")

    repo = SqlUserRepository(session)
    user = await repo.get_by_id(claims["sub"])
    if user is None:
        raise UnauthorizedError("User not found")

    return user
