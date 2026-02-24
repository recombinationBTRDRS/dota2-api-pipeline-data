# Dota Analytics Platform

Аналітична платформа для гри Dota 2: збір матчів, нормалізація даних, побудова статистики,
рекомендацій білдів, ролей, таймінгів та аналітики контрів і синергій.

## 🎯 Мета проєкту
- Побудувати масштабовану data-платформу для аналізу матчів
- Навчитись працювати з великими обʼємами даних
- Реалізувати мікросервісну архітектуру
- Побудувати рекомендаційну систему для білдів героїв

## 🧱 Архітектура (High-Level)
- Match Discovery Service — пошук матчів за фільтрами
- Ingestion Service — завантаження raw JSON з API
- Normalization Service — перетворення у внутрішні моделі
- Storage Service — робота з БД
- Public API — видача даних для фронтенду
- Analytics Service — статистика та рекомендації

## 🛠 Технології
- Python 3.12
- FastAPI
- SQLAlchemy + Alembic
- SQLite (dev) → PostgreSQL (prod)
- Redis / Celery (черги)
- Docker + Docker Compose
- GitHub Actions (CI/CD)
- Pytest, Ruff, MyPy

## 📦 Структура репозиторію
services/
ingestion/
normalization/
match-discovery/
storage/
api/
analytics/
docs/
docker-compose.yml


## 🚀 Як запустити локально
```bash
docker-compose up --build


---

## 3️⃣ High-Level план роботи (docs/high-level-plan.md)

```md
# High-Level Roadmap

## Phase 1 — Foundation
- Архітектура репозиторію
- CI/CD + автотести
- Проєктування БД
- DTO + парсинг JSON

## Phase 2 — Data Pipeline
- Match Discovery Service
- Ingestion Service
- Normalization Service
- Storage Service

## Phase 3 — Public API
- API для героїв, матчів, предметів
- Документація API

## Phase 4 — Analytics
- Ролі героїв
- Рекомендації білдів
- Контри і синергії

## Phase 5 — Scale & ML
- Черги
- Оптимізація БД
- ML-моделі
- Моніторинг