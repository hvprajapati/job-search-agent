"""Auth API routes."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
)
from pathfinder.identity.domain.entities import User
from pathfinder.identity.domain.value_objects import Email
from pathfinder.identity.domain.exceptions import (
    InvalidCredentialsError, EmailAlreadyExistsError, WeakPasswordError,
)
from pathfinder.identity.infrastructure.persistence.user_repository import SqlUserRepository
from pathfinder.identity.infrastructure.auth.password_hasher import hash_password, verify_password
from pathfinder.identity.infrastructure.auth.jwt_service import JWTService

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = SqlUserRepository(session)
    email = Email(value=body.email.strip().lower())

    if await repo.email_exists(email):
        raise EmailAlreadyExistsError(body.email)

    user = User.register(email=body.email, full_name=body.full_name)
    user.set_password_hash(hash_password(body.password))
    await repo.save(user)

    jwt_svc = JWTService()
    access = jwt_svc.create_access_token(str(user.id), "default", user.tier.value)
    refresh = jwt_svc.create_refresh_token(str(user.id), str(user.id))

    return {
        "data": {
            "tokens": {"access_token": access, "token_type": "bearer", "expires_in": 900},
            "user": {
                "user_id": str(user.id), "email": user.email.value,
                "full_name": user.full_name, "tier": user.tier.value,
                "has_profile": False,
            },
        }
    }


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    repo = SqlUserRepository(session)
    email = Email(value=body.email.strip().lower())
    user = await repo.get_by_email(email)

    if user is None or user.hashed_password is None:
        raise InvalidCredentialsError()
    if not verify_password(user.hashed_password, body.password):
        raise InvalidCredentialsError()
    if not user.is_active:
        raise InvalidCredentialsError()

    user.record_login()
    await repo.save(user)

    jwt_svc = JWTService()
    access = jwt_svc.create_access_token(str(user.id), "default", user.tier.value)
    refresh = jwt_svc.create_refresh_token(str(user.id), str(user.id))

    return {
        "data": {
            "tokens": {"access_token": access, "token_type": "bearer", "expires_in": 900},
            "user": {
                "user_id": str(user.id), "email": user.email.value,
                "full_name": user.full_name, "tier": user.tier.value,
                "has_profile": False,
            },
        }
    }


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    current_user: User | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Revoke the current session token. Uses token hash blacklisting."""
    import hashlib
    import logging
    from pathfinder.shared.infrastructure.redis import get_redis

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Blacklist token hash in Redis with TTL matching token expiry
        try:
            redis_gen = get_redis()
            redis_client = await anext(redis_gen)
            await redis_client.setex(f"blacklist:token:{token_hash}", 900, "1")
            await redis_client.aclose()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to blacklist token: {e}")

    return Response(status_code=204)
