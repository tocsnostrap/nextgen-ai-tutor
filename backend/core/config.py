"""
Configuration management for NextGen AI Tutor
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "NextGen AI Tutor"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    # Database - PostgreSQL + TimescaleDB
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/ai_tutor",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=40, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    REDIS_POOL_SIZE: int = Field(default=50, env="REDIS_POOL_SIZE")
    
    # JWT
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        env="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )
    
    # AI Model Serving
    AI_MODEL_SERVER_URL: str = Field(
        default="http://localhost:8001",
        env="AI_MODEL_SERVER_URL"
    )
    BKT_MODEL_PATH: str = Field(
        default="/models/bkt/model.pkl",
        env="BKT_MODEL_PATH"
    )
    EMOTION_MODEL_PATH: str = Field(
        default="/models/emotion/model.pkl",
        env="EMOTION_MODEL_PATH"
    )
    
    # Learning Analytics
    ANALYTICS_BATCH_SIZE: int = Field(default=1000, env="ANALYTICS_BATCH_SIZE")
    ANALYTICS_FLUSH_INTERVAL: int = Field(default=60, env="ANALYTICS_FLUSH_INTERVAL")  # seconds
    
    # WebSocket
    WEBSOCKET_MAX_CONNECTIONS: int = Field(
        default=10000,
        env="WEBSOCKET_MAX_CONNECTIONS"
    )
    WEBSOCKET_PING_INTERVAL: int = Field(default=30, env="WEBSOCKET_PING_INTERVAL")  # seconds
    WEBSOCKET_PING_TIMEOUT: int = Field(default=10, env="WEBSOCKET_PING_TIMEOUT")  # seconds
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds
    
    # File Storage
    UPLOAD_DIR: str = Field(default="/uploads", env="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = Field(default=100 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 100MB
    
    # Email
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: str = Field(default="", env="SMTP_USER")
    SMTP_PASSWORD: str = Field(default="", env="SMTP_PASSWORD")
    
    # Cache
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")  # seconds
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must start with postgresql://")
        return v
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must start with redis://")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Export settings
__all__ = ["settings"]