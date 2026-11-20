"""
Configuration management for NextGen AI Tutor
"""

import os
import secrets
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings"""

    APP_NAME: str = "NextGen AI Tutor"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")

    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=5000)
    WORKERS: int = Field(default=1)

    # The page is served by this app, so no cross-origin access is needed by default.
    CORS_ORIGINS: List[str] = Field(default=[])

    # Lets the built-in demo child (the page's hard-coded token) use the app.
    # For previews with no real data only. Never enable alongside real children.
    DEMO_MODE: bool = Field(default=False)

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/ai_tutor"
    )
    DATABASE_POOL_SIZE: int = Field(default=5)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)

    REDIS_URL: Optional[str] = Field(default=None)
    REDIS_POOL_SIZE: int = Field(default=10)
    REDIS_ENABLED: bool = Field(default=False)

    # No built-in default: required in production, random per start otherwise.
    SECRET_KEY: Optional[str] = Field(default=None)
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Claude models. TUTOR_MODEL teaches, plans and marks; FAST_MODEL does routing.
    TUTOR_MODEL: str = Field(default="claude-sonnet-5-5")
    FAST_MODEL: str = Field(default="claude-haiku-5-5")

    ANALYTICS_BATCH_SIZE: int = Field(default=100)
    ANALYTICS_FLUSH_INTERVAL: int = Field(default=60)

    WEBSOCKET_MAX_CONNECTIONS: int = Field(default=100)
    WEBSOCKET_PING_INTERVAL: int = Field(default=30)
    WEBSOCKET_PING_TIMEOUT: int = Field(default=10)

    PROMETHEUS_ENABLED: bool = Field(default=False)
    SENTRY_DSN: Optional[str] = Field(default=None)

    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_PERIOD: int = Field(default=60)

    UPLOAD_DIR: str = Field(default="/tmp/uploads")
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024)

    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")

    CACHE_TTL: int = Field(default=300)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @model_validator(mode="after")
    def require_secret_key(self):
        if not self.SECRET_KEY:
            if self.ENVIRONMENT == "production":
                raise ValueError("SECRET_KEY must be set when ENVIRONMENT=production")
            self.SECRET_KEY = secrets.token_urlsafe(48)
        return self

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v):
        if v:
            if "?" in v:
                v = v.split("?")[0]
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()

__all__ = ["settings"]
