from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables.

    Uses Pydantic BaseSettings to automatically validate and cast
    environment variables to the correct Python types.
    """

    PROJECT_NAME: str
    PROJECT_VERSION: str

    API_V1_STR: str
    ENVIRONMENT: str
    LOG_LEVEL: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    DEFAULT_PAGE_LIMIT: int

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_TTL_SECONDS: int

    TICKET_RESERVATION_TIME_SECONDS: int

    @property
    def DATABASE_URL(self) -> str:
        """Construct the asynchronous PostgreSQL connection string.

        Combines individual database credentials into a fully qualified
        asyncpg URL format required by SQLAlchemy 2.0.
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        """Construct the Redis connection string."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_ignore_empty=True, extra="ignore"
    )


settings = Settings()
