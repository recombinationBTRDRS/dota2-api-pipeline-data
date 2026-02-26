# services/ingestion/app/state.py
"""Глобальний стан додатку.

Зберігає останню статистику циклу runner для /stats endpoint.
Оновлюється runner-ом після кожного run_cycle().
"""
from dataclasses import dataclass


@dataclass
class AppState:
    """Стан додатку що шариться між runner і FastAPI."""

    last_cycle_at: int | None = None        # unix timestamp останнього циклу
    last_cycle_stats: dict | None = None    # серіалізований CycleStats


# Singleton — імпортується звідусіль як `from services.ingestion.app.state import app_state`
app_state = AppState()