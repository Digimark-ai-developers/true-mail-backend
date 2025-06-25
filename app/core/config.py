import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "True Mail API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = (
        f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'truemail.db')}"
    )

    # JWT
    JWT_SECRET: str = "your-secret-key-here"  # Change this in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAILS_FROM_EMAIL: str
    EMAILS_FROM_NAME: Optional[str] = None
    FRONTEND_DOMAIN: str

    # Stripe
    STRIPE_SECRET_KEY: str = Field(..., description="Stripe Secret Key")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(None, description="Stripe Publishable Key")
    STRIPE_WEBHOOK_SECRET: str = Field(..., description="Stripe Webhook Secret")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
