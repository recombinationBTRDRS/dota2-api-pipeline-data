# Dota 2 Analytics Pipeline

Аналітична платформа для Dota 2: збір матчів з OpenDota API, нормалізація,
pre-computed статистика по героях, білдах, ролях, counter-picks і synergy.
Мікросервісна архітектура: Ingestion → Analysis → Frontend.

## Статус

![CI](https://github.com/recombinationBTRDRS/dota2-api-pipeline-data/actions/workflows/ci.yml/badge.svg)

**Version: v1.2.0**

| Сервіс | Технології | Порт | Статус |
|--------|-----------|------|--------|
| Ingestion | FastAPI + SQLite | :8000 | ✅ Production-ready |
| Analysis | FastAPI + SQLite | :8001 | 🔄 Epic 8 |
| Frontend | React + Vite | :5173 | ✅ Done |

| Epic | Назва | Статус |
|------|-------|--------|
| 1 | Ingestion Service MVP | ✅ Done |
| 2 | Match Discovery Service | ✅ Done |
| 3 | Domain Model (Heroes, Items, Roles) | ✅ Done |
| 4 | Analytics Engine | ✅ Done |
| R1 | Project Health, Refactor & Audit | ✅ Done |
| 5 | Pre-computed Data Layer | ✅ Done |
| 6 | Frontend (React + Vite + TypeScript) | ✅ Done |
| 7 | Data Scale & Quality | ✅ Done |
| 8 | Match Analysis Service | 🔄 In Progress |
| 9 | Draft Assistant | ⏳ Backlog |
| 10 | Team Builder | ⏳ Backlog |
| 11 | Scale & Production | ⏳ Backlog |

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
    └─ Explorer API ─────────────────► match discovery (--days, --before-match)

                    ↓
         Pre-computed Batch Jobs (Epic 5)
    hero_stats_computed / hero_item_build_computed
    hero_matchup_computed / hero_synergy_computed

                    ↓
    Ingestion API :8000          Analysis API :8001 (Epic 8)
    /heroes/{id}/stats           /watchlist/matches
    /analytics/meta              /reports/matches/{id}
    /computed/heroes/top         DraftAnalyzer + EconomyAnalyzer
    /computed/heroes/{id}/...

                    ↓
           Frontend :5173 (React + Vite + TypeScript)
```

**Шари Ingestion сервісу:**
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

# Ingestion сервіс
uvicorn services.ingestion.app.main:app --reload --port 8000
```

```bash
curl http://localhost:8000/health
# {"status": "ok", "db_ok": true}

curl http://localhost:8000/docs
# Swagger UI
```

---

## Наповнення БД

```bash
# Синхронізація героїв, items, ролей
python -c "
from services.ingestion.app.sync_heroes import sync_heroes
from services.ingestion.app.sync_items import sync_items
from services.ingestion.app.sync_role_scores import sync_role_scores
from services.ingestion.db.sqlite import init_db
init_db(); sync_heroes(); sync_items(); sync_role_scores()
"

# Матчі за останній тиждень, Divine+
python scripts/discover_and_ingest.py --count 200 --rank-tier 70 --days 7 --rebuild

# Матчі перед конкретним матчем (хронологічно)
python scripts/discover_and_ingest.py --count 200 --before-match 8714955447 --rank-tier 75

# Або з CSV
python scripts/batch_ingest.py --csv found.csv --rebuild
```

---

## Smoke Test

```bash
python scripts/smoke_test.py
# Перевіряє: sync → ingest → matchups → synergies → analytics
# 2 матчі, всі 6 секцій green
```

---

## Ingestion API (Epic 4 — raw queries)

| Endpoint | Опис |
|----------|------|
| `GET /heroes/{id}/stats` | Winrate, KDA, GPM для героя |
| `GET /heroes/{id}/stats/role/{pos}` | Статистика на позиції (1-5) |
| `GET /heroes/{id}/items` | Топ items за pickrate |
| `GET /analytics/meta` | Meta snapshot: winrate × pickrate |
| `GET /analytics/leaderboard/{pos}` | Топ героїв на позиції |
| `GET /analytics/hero/{id}/timeline` | Early/mid/late game статистика |

## Computed API (Epic 5 — pre-computed tables)

| Endpoint | Опис |
|----------|------|
| `POST /computed/rebuild` | Rebuild всіх pre-computed таблиць |
| `GET /computed/staleness` | Час останнього rebuild |
| `GET /computed/heroes/{id}/stats` | Pre-computed stats героя |
| `GET /computed/heroes/top` | Топ героїв за winrate |
| `GET /computed/heroes/{id}/items/{pos}` | Item build для героя на позиції |
| `GET /computed/heroes/{id}/matchups` | Counter-picks для героя |
| `GET /computed/heroes/{id}/synergies` | Synergy picks для героя |

## Analysis API (Epic 8 — окремий сервіс :8001)

| Endpoint | Опис |
|----------|------|
| `POST /watchlist/matches` | Додати матч у watchlist |
| `GET /watchlist/matches` | Список матчів у watchlist |
| `DELETE /watchlist/matches/{id}` | Видалити з watchlist |
| `POST /reports/matches/{id}` | Згенерувати аналіз матчу |
| `GET /reports/matches/{id}` | Отримати збережений звіт |

---

## Змінні середовища

| Змінна | Default | Опис |
|--------|---------|------|
| `OPENDOTA_BASE_URL` | `https://api.opendota.com/api` | Base URL |
| `OPENDOTA_RATE_LIMIT` | `60` | Запитів на хвилину |
| `OPENDOTA_TIMEOUT` | `30` | HTTP timeout (сек) |
| `OPENDOTA_RETRIES` | `3` | Retry при 429/5xx |
| `DISCOVERY_LOBBY_TYPE` | `7` | 7 = ranked |
| `DISCOVERY_MIN_RANK_TIER` | `70` | 70=Divine+, 75=Titan+, 80=Immortal+ |
| `DISCOVERY_INTERVAL_SEC` | `300` | Секунд між циклами runner |
| `DB_PATH` | `services/ingestion/db/data.sqlite` | SQLite файл |
| `LOG_LEVEL` | `INFO` | Рівень логування |
| `AUTO_REBUILD_AFTER_INGEST` | `True` | Rebuild після кожного ingest циклу |

---

## Розробка

```bash
pytest -q                                              # 296 passed
ruff check .
python -m mypy services/ --ignore-missing-imports --explicit-package-bases
python scripts/smoke_test.py
```

---

## Структура

```
services/
├── ingestion/                     ← Epics 1-7: збір + нормалізація + pre-computed
│   ├── app/
│   │   ├── main.py                ← FastAPI :8000
│   │   ├── routers/
│   │   │   ├── analytics.py       ← Epic 4
│   │   │   └── computed.py        ← Epic 5
│   │   ├── rebuild_*.py           ← Batch jobs
│   │   ├── ingest_match.py
│   │   ├── persist.py
│   │   └── sync_*.py
│   ├── db/
│   │   ├── schema.sql
│   │   ├── models.py
│   │   └── repositories/
│   ├── domains/
│   ├── providers/opendota/
│   └── tests/
│
├── analysis/                      ← Epic 8: Match Analysis (🔄 In Progress)
│   ├── app/
│   │   ├── main.py                ← FastAPI :8001
│   │   ├── routers/
│   │   │   ├── watchlist.py
│   │   │   └── reports.py
│   │   └── analyzers/
│   │       ├── draft.py
│   │       ├── economy.py
│   │       └── teamfight.py
│   ├── db/
│   └── tests/
│
└── frontend/                      ← Epic 6: React + Vite :5173
    └── src/
        ├── pages/
        └── api/

scripts/
├── batch_ingest.py                ← інгест з CSV
├── discover_and_ingest.py         ← discovery + інгест (--days, --before-match)
├── check_matches.py               ← перевірка radiant/dire split
└── smoke_test.py                  ← повний pipeline тест
```

---

## Документація

- [`docs/architecture.md`](docs/architecture.md) — knowledge snapshot
- [`docs/epics-and-tasks.md`](docs/epics-and-tasks.md) — повний roadmap
- [`scripts/README.md`](scripts/README.md) — довідка по скриптах

---

## Технології

**Python 3.11** · **FastAPI 0.115** · **Pydantic v2** · **SQLite** → PostgreSQL (Epic 11)
**React 19** · **Vite 7** · **TypeScript 5**
**httpx** · **requests** · **pytest** · **ruff** · **mypy** · **GitHub Actions**