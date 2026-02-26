#services/ingestion/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENDOTA_BASE_URL: str = "https://api.opendota.com/api"
    OPENDOTA_RATE_LIMIT: int = 60  # requests per minute
    OPENDOTA_TIMEOUT: int = 30     # seconds
    OPENDOTA_RETRIES: int = 3

    DB_PATH: str = "services/ingestion/db/data.sqlite"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()