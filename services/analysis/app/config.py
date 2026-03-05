# services/analysis/app/config.py
from pydantic_settings import BaseSettings
from pathlib import Path


class AnalysisConfig(BaseSettings):
    db_path: str = str(
        Path(__file__).parent.parent / "db" / "data.sqlite"
    )
    ingestion_api_url: str = "http://localhost:8000"
    port: int = 8001
    log_level: str = "INFO"

    model_config = {"env_prefix": "ANALYSIS_", "env_file": ".env", "extra": "ignore"}


config = AnalysisConfig()
