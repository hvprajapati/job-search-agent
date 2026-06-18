"""Application configuration via pydantic-settings."""
from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="forbid", case_sensitive=False,
    )

    app_env: Literal["local", "dev", "staging", "production"] = "local"
    app_debug: bool = False
    app_name: str = "pathfinder"
    app_cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = (
        "postgresql+asyncpg://pathfinder:pathfinder_dev@localhost:5432/pathfinder"
    )
    database_pool_size: int = 20
    database_pool_overflow: int = 10

    redis_url: str = "redis://localhost:6379/0"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout_seconds: int = 30
    deepseek_max_retries: int = 3

    openai_api_key: str = ""

    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_algorithm: str = "RS256"
    jwt_access_token_ttl: int = 900
    jwt_refresh_token_ttl: int = 604800

    resend_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    sentry_dsn: str = ""

    ff_enable_github_oauth: bool = False
    ff_enable_webhooks: bool = False

    @property
    def is_development(self) -> bool:
        return self.app_env in ("local", "dev")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
