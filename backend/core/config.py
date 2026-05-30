import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


class Settings:
    def __init__(self):
        env = os.getenv("ENV", "development").lower()
        fastapi_env = os.getenv("FASTAPI_ENV", "development").lower()
        is_production = env == "production" or fastapi_env == "production"

        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            if is_production:
                raise ValueError("DATABASE_URL must be configured in production")
            db_url = "postgresql+psycopg://smartonboard:smartonboard@localhost:5432/smartonboard"
        self.database_url = db_url

        secret = os.getenv("JWT_SECRET_KEY")
        if not secret or secret == "change-me-in-production":
            if is_production:
                raise ValueError("JWT_SECRET_KEY must be configured in production and cannot be default fallback")
            secret = "change-me-in-production"
        self.jwt_secret_key = secret

        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

        # Enforce Groq key presence in production
        if is_production and not os.getenv("GROQ_API_KEY"):
            raise ValueError("GROQ_API_KEY must be configured in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
