# services/ingestion/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenDota API
    OPENDOTA_BASE_URL: str = "https://api.opendota.com/api"
    OPENDOTA_RATE_LIMIT: int = 60  # requests per minute
    OPENDOTA_TIMEOUT: int = 30     # seconds
    OPENDOTA_RETRIES: int = 3

    # Match Discovery filters (Task 2.1)
    DISCOVERY_LOBBY_TYPE: int = 7      # 7 = ranked
    DISCOVERY_MIN_MMR: int = 3000      # avg_mmr filter
    DISCOVERY_LIMIT: int = 100         # matches per query
    DISCOVERY_PATCH: int | None = None # None = latest patch
    DISCOVERY_REGION: int | None = None  # None = all regions

    # Database
    DB_PATH: str = "services/ingestion/db/data.sqlite"

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()