2️⃣ Повний список EPIC → TASK (High-Level Roadmap)

Це твій технічний план проєкту, який можна винести в:

docs/epics-and-tasks.md

GitHub Projects (Epic → Tasks → Issues)

🧱 EPIC 1 — Foundation & Architecture

Ціль: технічний фундамент

TASK 1.1 — Repo bootstrap

Git flow

CI/CD

автотести

базова структура сервісів

TASK 1.2 — API DTO & JSON Parsing

fixtures реальних матчів

DTO

парсери

тести

TASK 1.3 — Relational DB Schema Design

ER-модель

нормалізація

первинні/зовнішні ключі

TASK 1.4 — SQLAlchemy Models + Migrations

ORM-моделі

Alembic

SQLite schema

🔌 EPIC 2 — Data Ingestion Pipeline

Ціль: стабільний ingestion пайплайн

TASK 2.1 — OpenDota API Client

retry

rate limit handling

backoff

TASK 2.2 — Match Discovery Service

фільтри матчів

регіон

рейтинг

часові вікна

TASK 2.3 — Raw Data Storage

збереження JSON

дедуплікація

TASK 2.4 — Normalization Pipeline

DTO → DB

валідація

idempotency

🗃 EPIC 3 — Domain Model (Heroes, Items, Skills, Roles)

Ціль: доменна модель гри

TASK 3.1 — Heroes

базові поля

hero_details

TASK 3.2 — Skills & Talents

порядок прокачки

ліві/праві таланти

TASK 3.3 — Items

ціна

ефективність

категорії

TASK 3.4 — Roles

core/support

role score (winrate + pickrate + performance)

📊 EPIC 4 — Analytics Engine

Ціль: корисна статистика

TASK 4.1 — Winrate / Pickrate

TASK 4.2 — Hero Performance by Role

TASK 4.3 — Item Build Popularity

TASK 4.4 — Skill Build Popularity

TASK 4.5 — Talent Picks

🧠 EPIC 5 — Recommendation Engine (AI / ML)

Ціль: рекомендації

TASK 5.1 — Rule-based Recommendations (MVP)

TASK 5.2 — Counter & Synergy

TASK 5.3 — Draft Analyzer (10 heroes → best builds)

TASK 5.4 — Win Probability Estimation

TASK 5.5 — ML Models (optional, later)

🌐 EPIC 6 — Public API & Frontend Ready

Ціль: підготовка до фронтенду

TASK 6.1 — Public API

TASK 6.2 — Filters & Pagination

TASK 6.3 — API Docs

TASK 6.4 — Caching

🚀 EPIC 7 — Scale & Production

Ціль: production-підготовка

TASK 7.1 — PostgreSQL

TASK 7.2 — Redis / Celery

TASK 7.3 — Async ingestion

TASK 7.4 — Monitoring & Logs

TASK 7.5 — Docker Compose

🧠 Як з цим працювати в GitHub

У GitHub Projects:

Columns:

Backlog

In Progress

In Review

Done

Issues naming:

`[EPIC-1][TASK-1.2] OpenDota JSON parsing`
`[EPIC-2][TASK-2.1] OpenDota API client`