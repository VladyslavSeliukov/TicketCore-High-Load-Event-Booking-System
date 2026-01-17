import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = 'TicketCore'
    PROJECT_VERSION: str = '0.1.0'

    API_V1_STR: str = '/api/v1'
    ENVIRONMENT: str = 'dev'

    DEFAULT_PAGE_LIMIT: int = 100
    DEFAULT_OFFSET: int = 0

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    @property
    def DATABASE_URL(self):
        return (
            f'postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}'
            f'@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}'
        )

    model_config = SettingsConfigDict(
        env_file='.env',
        env_ignore_empty=True,
        extra='ignore'
    )

settings = Settings()