# services/ingestion/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenDota API
    OPENDOTA_BASE_URL: str = "https://api.opendota.com/api"
    OPENDOTA_RATE_LIMIT: int = 60
    OPENDOTA_TIMEOUT: int = 30
    OPENDOTA_RETRIES: int = 3

    # Match Discovery filters (Task 2.1)
    DISCOVERY_LOBBY_TYPE: int = 7
    DISCOVERY_MIN_MMR: int = 3000
    DISCOVERY_LIMIT: int = 100
    DISCOVERY_PATCH: int | None = None
    DISCOVERY_REGION: int | None = None

    # Runner (Task 2.2)
    DISCOVERY_INTERVAL_SEC: int = 300

    # Database
    DB_PATH: str = "services/ingestion/db/data.sqlite"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Epic 5.6 — Pre-computed layer scheduler
    # True  → rebuild hero_stats_computed + hero_item_build_computed після кожного циклу
    # False → тільки manual trigger через POST /computed/rebuild
    AUTO_REBUILD_AFTER_INGEST: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()