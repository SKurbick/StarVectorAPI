import json

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_MIN_CONN_COUNT: int = 1
    POSTGRES_MAX_CONN_COUNT: int = 10
    POSTGRES_MAX_CONN_INACTIVE_LIFETIME: int = 300

    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str
    CLICKHOUSE_DB: str
    CLICKHOUSE_HOST: str
    CLICKHOUSE_PORT: str

    TOKENS_FILE_NAME: str

    APP_NAME: str = "StarVectorAPI"
    APP_IP_ADDRESS: str
    APP_PORT: int
    FRONTEND_API_ADDRESS: str
    FRONTEND_PORT: int
    CORS_ALLOW_ORIGINS: list[str] | None = None
    SCHEDULER_API_KEY: str

    JWT_ALGORITHM: str
    JWT_SECRET_KEY: SecretStr
    JWT_ISSUER: str | None = None
    JWT_ACCESS_AUDIENCE: str | None = None
    ACCESS_TOKEN_COOKIE_NAME: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


    @property
    def cors_allow_origins(self) -> list[str]:
        """
        Получить разрешенные origins для credentialed CORS-запросов.
        """
        if self.CORS_ALLOW_ORIGINS:
            return self.CORS_ALLOW_ORIGINS

        return [f"http://{self.FRONTEND_API_ADDRESS}:{self.FRONTEND_PORT}"]


settings: Settings = Settings()


async def get_wb_tokens() -> dict[str, str]:
    with open(settings.TOKENS_FILE_NAME, "r", encoding='utf-8') as file:
        tokens = json.load(file)
    return {acc.capitalize(): token for acc, token in tokens.items()}
