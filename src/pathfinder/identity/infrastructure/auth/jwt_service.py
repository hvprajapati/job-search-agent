"""JWT RS256 token service."""
import uuid
from datetime import datetime, timezone, timedelta
from jose import jwt
from pathfinder.shared.config import get_settings


class JWTService:
    def __init__(self) -> None:
        settings = get_settings()
        self._private_key = settings.jwt_private_key.encode()
        self._public_key = settings.jwt_public_key.encode()
        self._algorithm = settings.jwt_algorithm
        self._access_ttl = settings.jwt_access_token_ttl
        self._refresh_ttl = settings.jwt_refresh_token_ttl

    def create_access_token(
        self, user_id: str, tenant_id: str, tier: str,
        permissions: list[str] | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "tier": tier,
            "permissions": permissions or [],
            "type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=self._access_ttl),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(claims, self._private_key, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: str, family_id: str) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": user_id,
            "family_id": family_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(seconds=self._refresh_ttl),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(claims, self._private_key, algorithm=self._algorithm)

    def decode(self, token: str) -> dict:
        return jwt.decode(token, self._public_key, algorithms=[self._algorithm])

    def decode_without_expiry(self, token: str) -> dict:
        return jwt.decode(
            token, self._public_key, algorithms=[self._algorithm],
            options={"verify_exp": False},
        )
