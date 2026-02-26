# Dota 2 Analytics Pipeline

Аналітична платформа для Dota 2: збір матчів з OpenDota API, нормалізація,
збереження в SQLite та побудова статистики по героях, білдах і ролях.

## Статус

![CI](https://github.com/recombinationBTRDRS/taskflow/actions/workflows/ci.yml/badge.svg?branch=feat/epic-1-ingestion-bootstrap)

**Epic 1 — Ingestion Service MVP:** ✅ завершено

---

## Архітектура

```
OpenDota API
    │
    ▼
providers/opendota/
    client.py        ← sync HTTP + rate limit + retry/backoff
    async_client.py  ← async варіант
    adapters.py      ← raw JSON → normalized contract dict
    │
    ▼
domains/matches/
    parsers.py       ← contract dict → Match DTO (pydantic validation)
    dtos.py          ← PlayerMatchStats, Match
    │
    ▼
app/
    persist.py       ← domain → DB models, єдина точка конвертації
    ingest_match.py  ← orchestration: fetch → adapt → parse → persist
    │
    ▼
db/
    repositories.py  ← MatchRepository, PlayerRepository, MatchPlayerRepository
    unit_of_work.py  ← атомарні транзакції (BEGIN / COMMIT / ROLLBACK)
    schema.sql       ← matches, players, match_players
    sqlite.py        ← connection, init_db
```

**Ізоляція шарів:** `domain` не знає про `db`, `db` не знає про `domain`,
`providers` не знають про `db`.

---

## Швидкий старт

```bash
git clone https://github.com/recombinationBTRDRS/taskflow.git
cd taskflow

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Скопіюй `.env.example` → `.env` і за потреби зміни значення:

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

# Форматування
ruff format .

# Type check
python -m mypy services/ --ignore-missing-imports --explicit-package-bases
```

---

## Структура репозиторію

```
services/
└── ingestion/
    ├── app/
    │   ├── config.py          # pydantic-settings
    │   ├── ingest_match.py    # orchestration pipeline
    │   ├── main.py            # FastAPI app, lifespan, /health
    │   └── persist.py         # domain → DB, UnitOfWork
    ├── db/
    │   ├── models.py          # DB dataclasses
    │   ├── repositories.py    # MatchRepository, PlayerRepository, MatchPlayerRepository
    │   ├── schema.sql         # DDL
    │   ├── sqlite.py          # connection, init_db
    │   └── unit_of_work.py    # транзакційний контекст
    ├── domains/
    │   └── matches/
    │       ├── dtos.py        # Match, PlayerMatchStats (pydantic)
    │       └── parsers.py     # parse_match()
    ├── providers/
    │   └── opendota/
    │       ├── adapters.py    # raw JSON → contract dict
    │       ├── async_client.py
    │       └── client.py      # MatchProvider Protocol + OpenDotaClient
    └── tests/
        ├── app/
        ├── db/
        ├── domains/
        ├── integration/
        └── providers/
docs/
├── epics-and-tasks.md         # roadmap
└── architecture.md
```

---

## Технології

- **Python 3.11+**
- **FastAPI 0.115** + Uvicorn
- **Pydantic v2** + pydantic-settings
- **SQLite** (dev) → PostgreSQL (prod, Epic 7)
- **httpx** (async HTTP) + **requests** (sync HTTP)
- **pytest** + pytest-asyncio + pytest-cov
- **ruff** (lint + format) + **mypy** (type check)
- **GitHub Actions** (CI)

---

## Roadmap

| Epic | Назва | Статус |
|------|-------|--------|
| 1 | Ingestion Service MVP | ✅ Done |
| 2 | Match Discovery Service | 🔜 Next |
| 3 | Domain Model (Heroes, Items, Roles) | ⏳ Backlog |
| 4 | Analytics Engine | ⏳ Backlog |
| 5 | Recommendation Engine | ⏳ Backlog |
| 6 | Public API | ⏳ Backlog |
| 7 | Scale & Production | ⏳ Backlog |

Детальний план: [`docs/epics-and-tasks.md`](docs/epics-and-tasks.md)