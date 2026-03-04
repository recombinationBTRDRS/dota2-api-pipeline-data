# services/ingestion/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenDota API
    OPENDOTA_BASE_URL: str = "https://api.opendota.com/api"
    OPENDOTA_RATE_LIMIT: int = 60
    OPENDOTA_TIMEOUT: int = 30
    OPENDOTA_RETRIES: int = 3

    # Match Discovery filters
    DISCOVERY_LOBBY_TYPE: int = 7
    # Epic 7.1: avg_mmr видалено з OpenDota public_matches.
    # Замінено на avg_rank_tier: 60=Ancient+, 70=Divine+, 80=Immortal+
    DISCOVERY_MIN_RANK_TIER: int = 60
    DISCOVERY_LIMIT: int = 100
    DISCOVERY_PATCH: int | None = None
    DISCOVERY_REGION: int | None = None

    # Runner
    DISCOVERY_INTERVAL_SEC: int = 300

    # Database
    DB_PATH: str = "services/ingestion/db/data.sqlite"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Epic 5.6 — Pre-computed layer scheduler
    AUTO_REBUILD_AFTER_INGEST: bool = True

    # Epic 6.6 — CORS (Frontend dev server)
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    def cors_origins_list(self) -> list[str]:
        """Повертає CORS_ORIGINS як список рядків."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()