# Dota 2 Analytics Pipeline

Аналітична платформа для Dota 2: збір матчів з OpenDota API, нормалізація,
побудова pre-computed статистики по героях, білдах і ролях.

## Статус

![CI](https://github.com/recombinationBTRDRS/dota2-api-pipeline-data/actions/workflows/ci.yml/badge.svg)

| Epic | Назва | Статус |
|------|-------|--------|
| 1 | Ingestion Service MVP | ✅ Done |
| 2 | Match Discovery Service | ✅ Done |
| 3 | Domain Model (Heroes, Items, Roles) | ✅ Done |
| 4 | Analytics Engine | ✅ Done |
| R1 | Project Health, Refactor & Audit | 🔜 Next |
| 5 | Pre-computed Data Layer | ⏳ Backlog |
| 6 | Frontend (React) | ⏳ Backlog |
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
    └─ Explorer API ─────────────────► match discovery (Epic 2)

                    ↓
         Pre-computed Batch Jobs (Epic 5)
    hero_aggregated_stats / hero_matchup_stats / hero_item_build_stats

                    ↓
           Analytics API (Epic 4)
    /heroes/{id}/stats  /analytics/meta  /analytics/leaderboard/{pos}

                    ↓
           Frontend (Epic 6)
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
```

---

## Analytics API

| Endpoint | Опис |
|----------|------|
| `GET /heroes/{id}/stats` | Winrate, KDA, GPM для героя |
| `GET /heroes/{id}/stats/role/{pos}` | Статистика на конкретній позиції (1-5) |
| `GET /heroes/{id}/items` | Топ items за pickrate |
| `GET /analytics/meta` | Meta snapshot: winrate × pickrate |
| `GET /analytics/leaderboard/{pos}` | Топ героїв на позиції |
| `GET /analytics/hero/{id}/timeline` | Early/mid/late game статистика |

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

---

## Розробка

```bash
pytest -q
ruff check .
python -m mypy services/ --ignore-missing-imports --explicit-package-bases
```

---

## Структура

```
services/ingestion/
├── app/
│   ├── config.py             ← pydantic-settings
│   ├── main.py               ← FastAPI, /health, /stats
│   ├── routers/analytics.py  ← analytics endpoints
│   ├── enrich.py             ← Match + HeroRepository → EnrichedPlayerStats
│   ├── ingest_match.py       ← orchestration pipeline
│   ├── persist.py            ← domain → DB (транзакція)
│   ├── sync_heroes.py
│   ├── sync_items.py
│   └── sync_role_scores.py
├── db/
│   ├── models.py
│   ├── repositories.py       ← → рефактор в Epic R1
│   ├── schema.sql
│   ├── sqlite.py
│   └── unit_of_work.py
├── domains/
│   ├── heroes/               ← Hero, EnrichedPlayerStats, HERO_META (125 heroes)
│   ├── items/
│   ├── matches/              ← Match, PlayerMatchStats
│   ├── roles/                ← Role enum
│   └── discovery/
├── providers/opendota/
│   ├── client.py / async_client.py
│   ├── adapters.py
│   ├── hero_id_map.py        ← static name→id map
│   └── explorer_client.py
└── tests/
    ├── app/ db/ domains/ providers/
    ├── integration/
    └── e2e/
```

---

## Документація

- [`docs/architecture.md`](docs/architecture.md) — knowledge snapshot: модулі, таблиці, gaps
- [`docs/epics-and-tasks.md`](docs/epics-and-tasks.md) — повний roadmap
- [`docs/high-level-plan.md`](docs/high-level-plan.md) — фазова карта продукту

---

## Технології

**Python 3.11** · **FastAPI 0.115** · **Pydantic v2** · **SQLite** → PostgreSQL (Epic 8)
**httpx** · **requests** · **pytest** · **ruff** · **mypy** · **GitHub Actions**