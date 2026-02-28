# Dota 2 Analytics Pipeline

Аналітична платформа для Dota 2: збір матчів з OpenDota API, нормалізація,
збереження в SQLite та побудова статистики по героях, білдах і ролях.

## Статус

![CI](https://github.com/recombinationBTRDRS/dota2-api-pipeline-data/actions/workflows/ci.yml/badge.svg)

| Epic | Назва | Статус |
|------|-------|--------|
| 1 | Ingestion Service MVP | ✅ Done |
| 2 | Match Discovery Service | ✅ Done |
| 3 | Domain Model (Heroes, Items, Roles) | ✅ Done |
| 4 | Analytics Engine | 🔜 Next |
| 5 | Recommendation Engine | ⏳ Backlog |
| 6 | Public API | ⏳ Backlog |
| 7 | Scale & Production | ⏳ Backlog |

---

## Архітектура

```
OpenDota API
    │
    ├─ /heroes ──────────────────► sync_heroes()
    ├─ /constants/items ─────────► sync_items()
    │                                   │
    │                             heroes / items tables
    │                                   │
    │                             sync_role_scores()
    │                             (HERO_META + OPENDOTA_HERO_IDS)
    │                                   │
    │                          hero_role_scores table
    │
    ├─ /matches/{id} ────────────► ingest_match()
    │       │
    │   adapters.py           raw JSON → contract dict
    │   parsers.py            contract dict → Match DTO
    │   persist.py            domain → DB models
    │       │
    │  matches / players / match_players tables
    │
    └─ Explorer API ─────────────► match discovery (Epic 2)

                    ▼
             enrich_match()
    Match DTO + HeroRepository → EnrichedPlayerStats
    (hero_name, primary_attr, attack_type, role)

                    ▼
           Analytics Engine (Epic 4)
```

**Ізоляція шарів:**
- `domains/` — чиста бізнес-логіка, без DB і HTTP
- `providers/` — тільки HTTP, без DB
- `db/` — тільки persistence, без domain logic
- `app/` — orchestration: з'єднує шари

---

## Швидкий старт

```bash
git clone https://github.com/recombinationBTRDRS/dota2-api-pipeline-data.git
cd dota2-api-pipeline-data

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Скопіюй `.env.example` → `.env`:

```bash
cp .env.example .env
```

Запуск сервісу:

```bash
uvicorn services.ingestion.app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

---

## Змінні середовища

| Змінна | За замовчуванням | Опис |
|--------|-----------------|------|
| `OPENDOTA_BASE_URL` | `https://api.opendota.com/api` | Base URL OpenDota API |
| `OPENDOTA_RATE_LIMIT` | `60` | Запитів на хвилину |
| `OPENDOTA_TIMEOUT` | `30` | HTTP timeout (секунди) |
| `OPENDOTA_RETRIES` | `3` | Кількість retry при 429/5xx |
| `DB_PATH` | `services/ingestion/db/data.sqlite` | Шлях до SQLite файлу |
| `LOG_LEVEL` | `INFO` | Рівень логування |

---

## Розробка

```bash
# Тести
pytest -q

# Lint
ruff check .

# Type check
python -m mypy services/ --ignore-missing-imports --explicit-package-bases
```

---

## Структура репозиторію

```
services/ingestion/
├── app/
│   ├── config.py             ← pydantic-settings
│   ├── enrich.py             ← enrich_match(): Match → EnrichedPlayerStats
│   ├── ingest_match.py       ← orchestration: fetch → adapt → parse → persist
│   ├── main.py               ← FastAPI app, /health
│   ├── persist.py            ← domain → DB
│   ├── sync_heroes.py        ← sync heroes від OpenDota → DB
│   ├── sync_items.py         ← sync items від OpenDota → DB
│   └── sync_role_scores.py   ← join HERO_META + hero_id_map → DB
├── db/
│   ├── models.py             ← DB dataclasses
│   ├── repositories.py       ← всі репозиторії
│   ├── schema.sql            ← DDL: matches, players, heroes, items, hero_role_scores
│   ├── sqlite.py             ← connection, init_db
│   └── unit_of_work.py       ← атомарні транзакції
├── domains/
│   ├── heroes/
│   │   ├── dtos.py           ← Hero, EnrichedPlayerStats (pydantic)
│   │   ├── meta.py           ← HeroMeta + HERO_META[name→scores], 125 героїв
│   │   └── parsers.py
│   ├── items/
│   │   ├── dtos.py
│   │   └── parsers.py
│   ├── matches/
│   │   ├── dtos.py           ← Match, PlayerMatchStats
│   │   └── parsers.py
│   ├── roles/
│   │   └── dtos.py           ← Role enum (CARRY=1..HARD_SUPPORT=5)
│   └── discovery/
│       ├── dtos.py
│       └── query_builder.py
├── providers/opendota/
│   ├── hero_id_map.py        ← OPENDOTA_HERO_IDS[name→id], 125 героїв
│   ├── heroes_client.py
│   ├── items_client.py
│   ├── adapters.py
│   ├── client.py
│   ├── async_client.py
│   └── explorer_client.py
└── tests/
    ├── app/                  ← unit: enrich, ingest, persist
    ├── db/                   ← unit: repositories
    ├── domains/              ← unit: parsers, meta, roles
    ├── integration/          ← real SQLite: sync flows
    ├── providers/            ← mock HTTP: clients
    └── e2e/                  ← full cycle sync → enrich → assert
```

---

## Технології

- **Python 3.11+**
- **FastAPI 0.115** + Uvicorn
- **Pydantic v2** + pydantic-settings
- **SQLite** (dev) → PostgreSQL (prod, Epic 7)
- **httpx** (async) + **requests** (sync)
- **pytest** + pytest-asyncio
- **ruff** (lint) + **mypy** (type check)
- **GitHub Actions** (CI)