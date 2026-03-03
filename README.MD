# Dota 2 Analytics Pipeline

Аналітична платформа для Dota 2: збір матчів з OpenDota API, нормалізація,
побудова pre-computed статистики по героях, білдах, ролях, counter-picks і synergy.

## Статус

![CI](https://github.com/recombinationBTRDRS/dota2-api-pipeline-data/actions/workflows/ci.yml/badge.svg)

**Version: 1.0.0**

| Epic | Назва | Статус |
|------|-------|--------|
| 1 | Ingestion Service MVP | ✅ Done |
| 2 | Match Discovery Service | ✅ Done |
| 3 | Domain Model (Heroes, Items, Roles) | ✅ Done |
| 4 | Analytics Engine | ✅ Done |
| R1 | Project Health, Refactor & Audit | ✅ Done |
| 5 | Pre-computed Data Layer | ✅ Done |
| 6 | Frontend (React) | 🔜 Next |
| 7 | Recommendation Engine | ⏳ Backlog |
| 8 | Public API & Scale | ⏳ Backlog |

---

## Архітектура

```
OpenDota API
    │
    ├─ /heroes, /constants/items ────► sync jobs → heroes, items tables
    │
    ├─ /matches/{id} ────────────────► ingest_match()
    │   adapters → parsers → persist
    │   matches / players / match_players / match_player_items
    │
    └─ Explorer API ─────────────────► match discovery (Runner)

                    ↓
         Pre-computed Batch Jobs (Epic 5)
    hero_stats_computed / hero_item_build_computed
    hero_matchup_computed / hero_synergy_computed

                    ↓
           Analytics API (Epic 4) + Computed API (Epic 5)
    /heroes/{id}/stats     /computed/heroes/{id}/stats
    /analytics/meta        /computed/heroes/top
    /computed/rebuild      /computed/staleness

                    ↓
           Frontend (Epic 6) — React/Vite/TypeScript
```

**Шари:**
- `providers/` — тільки HTTP, raw JSON → dict
- `domains/` — dict → Pydantic DTO, бізнес-сутності
- `db/` — persistence, repositories
- `app/` — orchestration, з'єднує шари

---

## Швидкий старт

```bash
git clone https://github.com/recombinationBTRDRS/dota2-api-pipeline-data.git
cd dota2-api-pipeline-data

python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env

uvicorn services.ingestion.app.main:app --reload
```

```bash
curl http://localhost:8000/health
# {"status": "ok", "db_ok": true}

curl http://localhost:8000/docs
# Swagger UI з усіма endpoints
```

---

## Smoke Test (реальні дані)

```bash
python scripts/smoke_test.py
# Запускає повний pipeline на 1 реальному матчі з OpenDota API
# Перевіряє sync, ingest, analytics
```

---

## Analytics API (Epic 4 — raw queries)

| Endpoint | Опис |
|----------|------|
| `GET /heroes/{id}/stats` | Winrate, KDA, GPM для героя |
| `GET /heroes/{id}/stats/role/{pos}` | Статистика на конкретній позиції (1-5) |
| `GET /heroes/{id}/items` | Топ items за pickrate |
| `GET /analytics/meta` | Meta snapshot: winrate × pickrate |
| `GET /analytics/leaderboard/{pos}` | Топ героїв на позиції |
| `GET /analytics/hero/{id}/timeline` | Early/mid/late game статистика |

## Computed API (Epic 5 — pre-computed tables)

| Endpoint | Опис |
|----------|------|
| `POST /computed/rebuild` | Rebuild всіх pre-computed таблиць (sync) |
| `GET /computed/staleness` | Час останнього rebuild |
| `GET /computed/heroes/{id}/stats` | Pre-computed stats героя (з rollups по patch/region) |
| `GET /computed/heroes/top` | Топ героїв за winrate |
| `GET /computed/heroes/{id}/items/{pos}` | Item build для героя на позиції |

Документація: `http://localhost:8000/docs`

---

## Змінні середовища

| Змінна | Default | Опис |
|--------|---------|------|
| `OPENDOTA_BASE_URL` | `https://api.opendota.com/api` | Base URL |
| `OPENDOTA_RATE_LIMIT` | `60` | Запитів на хвилину |
| `OPENDOTA_TIMEOUT` | `30` | HTTP timeout (сек) |
| `OPENDOTA_RETRIES` | `3` | Retry при 429/5xx |
| `DISCOVERY_LOBBY_TYPE` | `7` | 7 = ranked |
| `DISCOVERY_MIN_MMR` | `3000` | Мінімальний MMR |
| `DISCOVERY_INTERVAL_SEC` | `300` | Секунд між циклами |
| `DB_PATH` | `services/ingestion/db/data.sqlite` | SQLite файл |
| `LOG_LEVEL` | `INFO` | Рівень логування |
| `AUTO_REBUILD_AFTER_INGEST` | `True` | Rebuild pre-computed після кожного ingest циклу |

---

## Розробка

```bash
pytest -q
ruff check .
python -m mypy services/ --ignore-missing-imports --explicit-package-bases
python scripts/smoke_test.py
```

---

## Структура

```
services/ingestion/
├── app/
│   ├── config.py
│   ├── main.py                    ← FastAPI v1.0.0, /health, /stats
│   ├── runner.py                  ← Discovery + Ingest + Auto-rebuild scheduler
│   ├── routers/
│   │   ├── analytics.py           ← Epic 4 endpoints
│   │   └── computed.py            ← Epic 5 endpoints
│   ├── rebuild_hero_stats.py      ← Batch job: hero_stats_computed
│   ├── rebuild_item_builds.py     ← Batch job: hero_item_build_computed
│   ├── rebuild_matchups.py        ← Batch job: hero_matchup_computed
│   ├── rebuild_synergies.py       ← Batch job: hero_synergy_computed
│   ├── rebuild_all.py             ← Coordinator: rebuild все
│   ├── enrich.py
│   ├── ingest_match.py
│   ├── persist.py
│   ├── sync_heroes.py
│   ├── sync_items.py
│   └── sync_role_scores.py
├── db/
│   ├── models.py
│   ├── repositories/
│   │   ├── __init__.py            ← re-export всіх репозиторіїв
│   │   ├── base.py
│   │   ├── matches.py
│   │   ├── heroes.py
│   │   ├── items.py
│   │   ├── players.py
│   │   └── analytics/
│   │       ├── hero_stats.py
│   │       ├── item_build.py
│   │       ├── timeline.py
│   │       ├── computed.py        ← Epic 5
│   │       └── matchup.py         ← Epic 5.4/5.5
│   ├── schema.sql
│   ├── sqlite.py
│   └── unit_of_work.py
├── domains/
│   ├── heroes/
│   ├── items/
│   ├── matches/
│   ├── roles/
│   └── discovery/
├── providers/opendota/
└── tests/
    ├── app/
    ├── db/
    ├── domains/
    ├── providers/
    ├── integration/
    ├── e2e/
    └── seed_helpers.py
```

---

## Документація

- [`docs/architecture.md`](docs/architecture.md) — knowledge snapshot
- [`docs/epics-and-tasks.md`](docs/epics-and-tasks.md) — повний roadmap
- [`docs/high-level-plan.md`](docs/high-level-plan.md) — фазова карта

---

## Технології

**Python 3.11** · **FastAPI 0.115** · **Pydantic v2** · **SQLite** → PostgreSQL (Epic 8)
**httpx** · **requests** · **pytest** · **ruff** · **mypy** · **GitHub Actions**