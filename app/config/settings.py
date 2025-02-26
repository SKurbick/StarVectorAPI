import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    TOKENS_FILE: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings: Settings = Settings()


async def get_wb_tokens() -> dict:
    with open(settings.TOKENS_FILE_NAME, "r", encoding='utf-8') as file:
        tokens = json.load(file)
    return tokens
