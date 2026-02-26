# services/ingestion/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenDota API
    OPENDOTA_BASE_URL: str = "https://api.opendota.com/api"
    OPENDOTA_RATE_LIMIT: int = 60  # requests per minute
    OPENDOTA_TIMEOUT: int = 30     # seconds
    OPENDOTA_RETRIES: int = 3

    # Match Discovery filters (Task 2.1)
    DISCOVERY_LOBBY_TYPE: int = 7
    DISCOVERY_MIN_MMR: int = 3000
    DISCOVERY_LIMIT: int = 100
    DISCOVERY_PATCH: int | None = None
    DISCOVERY_REGION: int | None = None

    # Runner (Task 2.2)
    DISCOVERY_INTERVAL_SEC: int = 300  # секунд між циклами

    # Database
    DB_PATH: str = "services/ingestion/db/data.sqlite"

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()