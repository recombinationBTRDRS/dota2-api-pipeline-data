# High-Level Plan

## Phase 1 — Foundation
- Створення репозиторію
- Налаштування CI/CD
- Базова структура мікросервісів
- Проєктування БД (ER-діаграма)
- DTO для OpenDota JSON

## Phase 2 — Data Pipeline
- Match Discovery Service (jobs + filters)
- Ingestion Service (API client + retry)
- Normalization Service (mapping JSON → DB)
- Storage Service (SQLite → PostgreSQL)

## Phase 3 — Public API
- Ендпоінти для героїв, матчів, предметів
- Документація API (Swagger)

## Phase 4 — Analytics
- Ролі героїв (score)
- Рекомендації білдів
- Прокачка скілів і талантів
- Контри та синергії

## Phase 5 — Scale & ML
- Черги (Redis / Celery)
- Оптимізація запитів
- ML-моделі (прогноз winrate, білди)
- Моніторинг та логування