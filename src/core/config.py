from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "TicketCore"
    PROJECT_VERSION: str = "0.1.0"

    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "dev"
    LOG_LEVEL: str = "INFO"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DEFAULT_PAGE_LIMIT: int = 100

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_TTL_SECONDS: int = 10

    TICKET_RESERVATION_TIME_SECONDS: int = 900

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_ignore_empty=True, extra="ignore"
    )


settings = Settings()
