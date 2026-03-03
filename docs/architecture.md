# Architecture — Knowledge Snapshot
> Останнє оновлення: після Epic 5 (Pre-computed Data Layer) + R1.4 Smoke Test.
> Мета: не пояснювати заново при старті нової сесії.

---

## Загальне бачення архітектури

```
External APIs (OpenDota)
        ↓
  Raw Ingestion          ← match_players, matches, items, heroes
        ↓
  Pre-computed Tables    ← batch jobs (rebuild по тригеру або AUTO_REBUILD_AFTER_INGEST)
        ↓
  Analytics API          ← читає з pre-computed, не рахує по raw
        ↓
  Frontend / Consumers   ← Epic 6 (React/Vite)
```

**Ключова ідея:** pre-computed таблиці — бізнес-актив. Сирі матчі — тимчасовий матеріал.

---

## Поточні шари

```
HTTP (OpenDota API)
        ↓
  providers/opendota/     ← тільки HTTP, raw JSON → dict
        ↓
  domains/                ← dict → Pydantic DTO + валідація
        ↓
  app/                    ← orchestration: sync, ingest, enrich, persist, rebuild
        ↓
  db/                     ← SQL, repositories, models
        ↓
  SQLite (dev) → PostgreSQL (Epic 8)
```

**Правило ізоляції (жорстке):**
- `db/` — не імпортує з `domains/` і `providers/`
- `providers/` — не імпортує з `db/` і `domains/`
- `domains/` — не знає про HTTP і DB
- `app/` — єдиний хто з'єднує шари

---

## Що робить кожен модуль

### `app/`
| Файл | Що робить |
|------|-----------|
| `config.py` | pydantic-settings, ENV, всі налаштування |
| `main.py` | FastAPI v1.0.0, lifespan, /health, /stats |
| `runner.py` | Discovery + Ingest цикл + AUTO_REBUILD_AFTER_INGEST |
| `routers/analytics.py` | Epic 4 endpoints (raw query) |
| `routers/computed.py` | Epic 5 endpoints (pre-computed) |
| `rebuild_hero_stats.py` | Batch job: DELETE + INSERT hero_stats_computed (з Python rollups) |
| `rebuild_item_builds.py` | Batch job: DELETE + INSERT hero_item_build_computed |
| `rebuild_matchups.py` | Batch job: hero_matchup_computed (counter matrix) |
| `rebuild_synergies.py` | Batch job: hero_synergy_computed (synergy matrix) |
| `rebuild_all.py` | Coordinator: викликає всі rebuild functions |
| `sync_heroes.py` | OpenDota /heroes → heroes table |
| `sync_items.py` | OpenDota /constants/items → items table |
| `sync_role_scores.py` | HERO_META + hero_id_map → hero_role_scores table |
| `ingest_match.py` | fetch → adapt → parse → persist |
| `enrich.py` | Match DTO + HeroRepository → EnrichedPlayerStats |
| `persist.py` | Match domain → DB (одна транзакція) |
| `state.py` | In-memory стан останнього discovery циклу |

### `db/repositories/`
| Файл | Що робить |
|------|-----------|
| `__init__.py` | Re-export всіх репозиторіїв (backward compat) |
| `base.py` | `_EARLY_MAX`, `_MID_MAX`, `_MAX_ERROR_LEN` |
| `matches.py` | Match, MatchPlayer, MatchPlayerItem, IngestionLog write repos |
| `heroes.py` | Hero, HeroRoleScore write repos |
| `items.py` | Item write repo |
| `players.py` | Player write repo |
| `analytics/hero_stats.py` | HeroStatsRepository (winrate/KDA, role leaderboard) |
| `analytics/item_build.py` | ItemBuildRepository (item popularity) |
| `analytics/timeline.py` | MatchTimelineRepository (early/mid/late, meta snapshot) |
| `analytics/computed.py` | ComputedStatsRepository (pre-computed reads, Epic 5) |
| `analytics/matchup.py` | MatchupRepository (counter + synergy matrix reads, Epic 5.4/5.5) |

---

## Таблиці БД

### Raw data
| Таблиця | PK | Що зберігає | Стан |
|---------|----|-------------|------|
| `matches` | `id` | match_id, duration, radiant_win, start_time, patch, region | ✅ patch і region заповнюються |
| `players` | `id` (autoincrement) | account_id | rank_tier, mmr — не збираємо |
| `match_players` | `(match_id, player_slot)` | hero_id, kills, deaths, assists, gpm, xpm, win, lane_role, is_roaming | lane_role NULL (матч не парсений) |
| `match_player_items` | `(match_id, player_slot, slot)` | item_id (slots 0-5) | backpack (6-8), neutral — не збираємо |
| `ingestion_log` | `match_id` | status, ingested_at, error | |
| `heroes` | `id` | name, localized_name, primary_attr, attack_type | 127 героїв |
| `items` | `id` | name, localized_name, cost, flags | 470 items |
| `hero_role_scores` | `hero_id` | pos1-5, flex_score, primary_pos | 126/127 (Grimstroke gap) |

### Pre-computed (Epic 5)
| Таблиця | PK | Що зберігає | Особливості |
|---------|----|-------------|------------|
| `hero_stats_computed` | `id` (AUTOINCREMENT) | winrate, KDA, GPM по hero+pos+patch+region | UNIQUE index з COALESCE(-1); rollups (NULL patch/region) |
| `hero_item_build_computed` | `(hero_id, primary_pos, item_id)` | times_bought, times_won | |
| `hero_matchup_computed` | `(hero_id, opponent_id)` | matches, wins (обидва напрямки) | is_radiant = player_slot < 128 |
| `hero_synergy_computed` | `(hero_id, ally_id)` | matches, wins | hero_id < ally_id завжди |

---

## Analytics API endpoints

### Epic 4 (raw queries)
```
GET /heroes/{id}/stats                 → winrate, KDA, GPM
GET /heroes/{id}/stats/role/{pos}      → stats на конкретній позиції
GET /heroes/{id}/items                 → топ items за pickrate
GET /analytics/meta                    → meta snapshot (winrate × pickrate)
GET /analytics/leaderboard/{pos}       → топ по позиції
GET /analytics/hero/{id}/timeline      → early/mid/late stats
```

### Epic 5 (pre-computed)
```
POST /computed/rebuild                 → rebuild всіх pre-computed таблиць
GET  /computed/staleness               → час останнього rebuild
GET  /computed/heroes/{id}/stats       → pre-computed stats з rollups
GET  /computed/heroes/top              → топ за winrate
GET  /computed/heroes/{id}/items/{pos} → item build
```

---

## Pre-computed rebuild flow

```
Runner.run_cycle()
    → ingest N matches
    → if ingested > 0 and AUTO_REBUILD_AFTER_INGEST:
        → _run_rebuild(stats)
            → rebuild_hero_stats()    ← Python rollup агрегація
            → rebuild_item_builds()
            → [matchups і synergies — manual trigger або окремий scheduler]
```

**Rollup логіка в `rebuild_hero_stats`:**
Один granular SELECT, потім Python dict агрегує 4 варіанти:
- `(patch, region)` — granular
- `(patch, None)` — rollup по регіонах
- `(None, region)` — rollup по патчах
- `(None, None)` — глобальний агрегат

Дублікати усуваються через dict key — якщо patch вже NULL в source, rollup не дублює.

---

## Відомі gaps і open questions

| Gap | Стан | Пріоритет |
|-----|------|-----------|
| `lane_role` / `is_roaming` | NULL (матч не парсений OpenDota) | 🟡 Середній |
| Grimstroke без role scores | HERO_META gap | 🟡 Середній |
| matchup/synergy endpoints | Batch jobs є, API endpoints — немає | 🔴 Треба додати |
| Backpack items (slots 6-8) | Не збираємо | 🟢 Низький |
| rank_tier, mmr | Не збираємо | 🟢 Низький |
| PostgreSQL migration | Epic 8 | ⏳ |
| Docker Compose | Epic 8 | ⏳ |

---

## Константи

### В `config.py` (через .env):
```
OPENDOTA_BASE_URL, OPENDOTA_RATE_LIMIT, OPENDOTA_TIMEOUT, OPENDOTA_RETRIES
DISCOVERY_LOBBY_TYPE, DISCOVERY_MIN_MMR, DISCOVERY_LIMIT, DISCOVERY_INTERVAL_SEC
DISCOVERY_PATCH, DISCOVERY_REGION, DB_PATH, LOG_LEVEL
AUTO_REBUILD_AFTER_INGEST
```

### Захардкоджені (кандидати на config — BL1.6):
```python
_EARLY_MAX = 1800    # base.py — межа early/mid фази
_MID_MAX = 3000      # base.py — межа mid/late фази
_MAX_ERROR_LEN = 500 # base.py — обрізка error string
flex_score >= 3      # sync_role_scores.py
range(6)             # adapters.py — item slots
```

---

## R1.4 Smoke Test результат (реальні дані)

Матч `8709253716`, OpenDota API, 2026-03:
- ✅ sync_heroes: 127 героїв
- ✅ sync_items: 470 items
- ✅ sync_role_scores: 126 записів (Grimstroke — gap в HERO_META)
- ✅ ingest_match: 10/10 гравців, patch=59, region=3
- ✅ account_id sentinel (4294967295) не зберігається
- ✅ match_player_items: 58 записів
- ✅ Analytics: HeroStats, MetaSnapshot, Timeline — відповіді коректні
- ⚠️ lane_role NULL для всіх 10 гравців (матч не парсений — очікувана поведінка)

---

## Структура тестів

```
tests/
├── app/
│   ├── test_enrich.py
│   ├── test_persist.py
│   ├── test_ingest_match.py
│   ├── test_analytics_endpoints.py
│   ├── test_computed_endpoints.py   ← Epic 5
│   └── test_runner_rebuild.py       ← Epic 5.6
├── db/
│   ├── test_repositories.py
│   ├── test_hero_stats_repository.py
│   ├── test_hero_role_stats_repository.py
│   ├── test_item_build_repository.py
│   ├── test_match_timeline_repository.py
│   ├── test_computed_repository.py  ← Epic 5
│   └── test_matchup_synergy.py      ← Epic 5.4/5.5
├── domains/
├── providers/
├── integration/
├── e2e/
└── seed_helpers.py                  ← shared test utilities
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
GitHub Actions CI
```