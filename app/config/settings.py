import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str
    CLICKHOUSE_DB: str
    CLICKHOUSE_HOST: str
    CLICKHOUSE_PORT: str

    TOKENS_FILE_NAME: str

    APP_IP_ADDRESS: str
    APP_PORT: int
    FRONTEND_API_ADDRESS: str
    FRONTEND_PORT: int
    SCHEDULER_API_KEY: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str
    REDIS_TIMEOUT: float
    REDIS_MAX_CONNECTIONS: int

    JWT_ALGORITHM: str
    JWT_SECRET_KEY: str

    MARKETPLACE_CARDS_APP_IP_ADDRESS: str
    MARKETPLACE_CARDS_APP_PORT: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings: Settings = Settings()


async def get_wb_tokens() -> dict[str, str]:
    with open(settings.TOKENS_FILE_NAME, "r", encoding='utf-8') as file:
        tokens = json.load(file)
    return tokens
