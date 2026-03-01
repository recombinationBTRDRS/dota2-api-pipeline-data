# Architecture — Knowledge Snapshot
> Файл-інвентаризація: що є зараз, як працює, що відомо про бізнес-логіку.
> Оновлювати при кожному рефакторингу або зміні логіки.
> Мета: не пояснювати заново при старті нової сесії.
> Останнє оновлення: після Epic 4.

---

## Загальне бачення архітектури

```
External APIs (OpenDota)
        ↓
  Raw Ingestion          ← match_players, matches, items, heroes
        ↓
  Pre-computed Tables    ← batch jobs (rebuild по тригеру або cron)
        ↓
  Analytics API          ← читає з pre-computed, не рахує по raw
        ↓
  Frontend / Consumers
```

**Ключова ідея:** pre-computed таблиці — бізнес-актив. Сирі матчі — тимчасовий матеріал.

---

## Поточні шари (після Epic 4)

```
HTTP (OpenDota API)
        ↓
  providers/opendota/     ← тільки HTTP, raw JSON → dict
        ↓
  domains/                ← dict → Pydantic DTO + валідація
        ↓
  app/                    ← orchestration: sync, ingest, enrich, persist
        ↓
  db/                     ← SQL, repositories, models
        ↓
  SQLite
```

**Правило ізоляції (жорстке):**
- `db/` — не імпортує з `domains/` і `providers/`
- `providers/` — не імпортує з `db/` і `domains/`
- `domains/` — не знає про HTTP і DB
- `app/` — єдиний хто з'єднує шари

---

## Що робить кожен модуль

### `providers/opendota/`
| Файл | Що робить |
|------|-----------|
| `client.py` | Синхронний HTTP, retry/backoff, rate limit |
| `async_client.py` | Async версія через httpx |
| `heroes_client.py` | GET /heroes |
| `items_client.py` | GET /constants/items |
| `explorer_client.py` | POST Explorer API (match discovery) |
| `adapters.py` | raw JSON → нормалізований dict (контракт між provider і domain) |
| `hero_id_map.py` | Статична мапа `name → opendota_id`, 125 героїв, вшита в код |

### `domains/`
| Файл | Що робить |
|------|-----------|
| `matches/dtos.py` | `Match`, `PlayerMatchStats` (Pydantic) |
| `matches/parsers.py` | dict → Match DTO |
| `heroes/dtos.py` | `Hero`, `EnrichedPlayerStats` (Pydantic) |
| `heroes/meta.py` | `HERO_META` — статичні бали pos1..pos5, 125 героїв, по імені |
| `heroes/parsers.py` | dict → Hero DTO |
| `items/dtos.py` | `Item` (Pydantic) |
| `items/parsers.py` | dict → Item DTO |
| `roles/dtos.py` | `Role` enum: CARRY=1, MID=2, OFFLANE=3, SUPPORT=4, HARD_SUPPORT=5 |
| `discovery/dtos.py` | Фільтри для пошуку матчів |
| `discovery/query_builder.py` | Будує SQL для Explorer API |

### `app/`
| Файл | Що робить |
|------|-----------|
| `config.py` | Всі налаштування через pydantic-settings + .env |
| `main.py` | FastAPI app, lifespan, /health, /stats |
| `routers/analytics.py` | Analytics endpoints (Epic 4) |
| `sync_heroes.py` | OpenDota /heroes → heroes table |
| `sync_items.py` | OpenDota /constants/items → items table |
| `sync_role_scores.py` | HERO_META + hero_id_map → hero_role_scores table |
| `ingest_match.py` | fetch → adapt → parse → persist |
| `enrich.py` | Match DTO + HeroRepository → EnrichedPlayerStats |
| `persist.py` | Match domain → DB (одна транзакція, batch items) |
| `state.py` | In-memory стан останнього discovery циклу |

### `db/` (поточний стан, перед R1 рефактором)
| Файл | Що робить |
|------|-----------|
| `schema.sql` | DDL всіх таблиць + індекси |
| `sqlite.py` | `get_connection()`, `init_db()`, `DB_PATH` |
| `unit_of_work.py` | Context manager для транзакцій |
| `models.py` | Dataclass'и що відповідають рядкам таблиць |
| `repositories.py` | Всі репозиторії — один файл ~800 рядків (**кандидат на R1 рефактор**) |

---

## Таблиці БД — поточний стан

| Таблиця | PK | Що зберігає | Примітки |
|---------|----|-------------|---------|
| `matches` | `id` | match_id, duration, radiant_win, start_time | `patch`, `region` — **завжди NULL** |
| `players` | `id` (autoincrement) | account_id | `rank_tier`, `mmr` — **завжди NULL** |
| `match_players` | `(match_id, player_slot)` | hero_id, kills, deaths, assists, gpm, xpm, win | `lane_role` **не збираємо** |
| `match_player_items` | `(match_id, player_slot, slot)` | item_id (slots 0-5) | backpack (6-8), neutral — **не збираємо** |
| `ingestion_log` | `match_id` | status, ingested_at, error | |
| `heroes` | `id` | name, localized_name, primary_attr, attack_type | |
| `items` | `id` | name, localized_name, cost, flags | |
| `hero_role_scores` | `hero_id` | pos1-5, flex_score, primary_pos | pre-computed з HERO_META |

---

## Репозиторії — поточний стан (перед R1)

**Write репозиторії:**
- `MatchRepository`, `MatchPlayerRepository`, `MatchPlayerItemRepository`
- `PlayerRepository`
- `IngestionLogRepository`
- `HeroRepository`, `HeroRoleScoreRepository`
- `ItemRepository`

**Analytics репозиторії (read-only, Epic 4):**
- `HeroStatsRepository` — winrate/pickrate/KDA (Task 4.1, 4.2)
- `ItemBuildRepository` — популярність items (Task 4.3)
- `MatchTimelineRepository` — early/mid/late + meta snapshot (Task 4.4)

**Analytics dataclasses:**
`HeroStatsRow`, `HeroRoleStatsRow`, `ItemBuildEntry`, `MetaHeroRow`, `MatchPhaseStatsRow`

---

## Analytics API endpoints (після Epic 4)

```
GET /heroes/{id}/stats                 → winrate, KDA, GPM
GET /heroes/{id}/stats/role/{pos}      → stats на конкретній позиції
GET /heroes/{id}/items                 → топ items за pickrate
GET /analytics/meta                    → meta snapshot (winrate × pickrate)
GET /analytics/leaderboard/{pos}       → топ по позиції
GET /analytics/hero/{id}/timeline      → early/mid/late stats
```

---

## Константи — де живуть

### В `config.py` (через .env):
```
OPENDOTA_BASE_URL, OPENDOTA_RATE_LIMIT, OPENDOTA_TIMEOUT, OPENDOTA_RETRIES
DISCOVERY_LOBBY_TYPE, DISCOVERY_MIN_MMR, DISCOVERY_LIMIT, DISCOVERY_INTERVAL_SEC
DISCOVERY_PATCH, DISCOVERY_REGION
DB_PATH, LOG_LEVEL
```

### Захардкоджені в коді — **кандидати на config:**
```python
_EARLY_MAX = 1800    # repositories.py — межа early/mid фази
_MID_MAX = 3000      # repositories.py — межа mid/late фази
_MAX_ERROR_LEN = 500 # repositories.py — обрізка error string
range(6)             # adapters.py — кількість item slots
flex_score_threshold  # sync_role_scores.py — поріг для flex hero
```

### Статичні дані вшиті в код (не в config, не в DB):
```python
HERO_META = {...}          # domains/heroes/meta.py — pos1-5 для 125 героїв
OPENDOTA_HERO_IDS = {...}  # providers/opendota/hero_id_map.py — name → id
```

---

## Відомі gaps і відкриті питання

### Поля що не збираємо але є в API:
| Поле | Де в API | Де мало б бути | Рішення |
|------|----------|---------------|---------|
| `lane_role` | player JSON | `match_players` | BL1.2 |
| `is_roaming` | player JSON | `match_players` | BL1.2 |
| `patch` | match JSON | `matches` | BL1.1 |
| `region` | match JSON | `matches` | BL1.1 |
| `rank_tier` | player JSON | `players` | BL1.1 |
| `backpack_0..2` | player JSON | `match_player_items` | BL1.3 |
| `item_neutral` | player JSON | `match_player_items` | BL1.3 |

### primary_pos — як рахується:
1. `HERO_META` (статика в коді) — бали pos1-5 по імені героя
2. `sync_role_scores.py` → `hero_role_scores` table
3. `primary_pos` = позиція з найвищим балом
4. **⚠️ Це статична оцінка**, не реальна позиція з матчу
5. В analytics (Task 4.2) використовується як proxy — approximation

### Що не перевірялось на реальних даних:
- Чи adapter коректно нормалізує всі поля real API
- Чи є розбіжності між fixtures і реальним JSON
- Чи analytics endpoints повертають розумні цифри

---

## Заплановані зміни (Epic 5 — Pre-computed Layer)

**Нові таблиці:**
```sql
hero_aggregated_stats     -- winrate, pickrate по patch/region
hero_role_aggregated_stats
hero_item_build_stats     -- топ builds
hero_matchup_stats        -- counter matrix (hero_a vs hero_b)
hero_synergy_stats        -- synergy matrix (hero_a with hero_b)
item_effectiveness
```

**Новий flow:**
```
Raw matches → Batch Job → Pre-computed Tables → Analytics API
```

Analytics API перейде з читання `match_players` на читання pre-computed таблиць.

---

## Структура тестів

```
tests/
├── app/
│   ├── test_enrich.py
│   ├── test_persist.py
│   ├── test_ingest_match.py
│   └── test_analytics_endpoints.py    ← FastAPI TestClient
├── db/
│   ├── test_repositories.py
│   ├── test_hero_stats_repository.py
│   ├── test_hero_role_stats_repository.py
│   ├── test_item_build_repository.py
│   └── test_match_timeline_repository.py
├── domains/
├── providers/
├── integration/
└── e2e/
    ├── test_domain_model_cycle.py
    └── test_analytics_cycle.py
```

---

## Версії технологій

```
Python 3.11+
FastAPI 0.115 + Uvicorn 0.29
Pydantic v2.12 + pydantic-settings 2.2
SQLite (dev) → PostgreSQL (Epic 8)
httpx 0.27 (async) + requests 2.31 (sync)
pytest 9.0 + pytest-asyncio
ruff 0.2 + mypy 1.8
```