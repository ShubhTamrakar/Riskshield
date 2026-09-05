import hashlib
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RiskShield"
    API_V1_STR: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────────────────────
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "riskshield"

    # Loaded from .env
    DATABASE_URL: str = ""

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Environment ───────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"

    # ── Security ──────────────────────────────────────────────────────────────
    API_KEY_HASH: str = ""

    # Comma-separated allowed CORS origins
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
        f"{self.POSTGRES_PASSWORD}@"
        f"{self.POSTGRES_SERVER}/"
        f"{self.POSTGRES_DB}"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def auth_enabled(self) -> bool:
        return bool(self.API_KEY_HASH)

    def verify_api_key(self, raw_key: str) -> bool:
        import hmac

        candidate_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return hmac.compare_digest(candidate_hash, self.API_KEY_HASH)


settings = Settings()