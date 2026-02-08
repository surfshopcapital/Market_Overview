"""Application settings using pydantic-settings."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    
    # Kalshi API (public endpoints only - no auth required)
    KALSHI_API_BASE_URL: str = Field(
        default="https://api.elections.kalshi.com/trade-api/v2",
        description="Kalshi API base URL"
    )
    
    # Email (SendGrid)
    SENDGRID_API_KEY: str = Field(..., description="SendGrid API key")
    EMAIL_FROM: str = Field(..., description="From email address")
    EMAIL_FROM_NAME: str = Field(
        default="Kalshi Markets Digest",
        description="From name for emails"
    )
    
    # Application
    APP_ENV: str = Field(default="production", description="Application environment")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    TIMEZONE: str = Field(default="America/New_York", description="Application timezone")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
