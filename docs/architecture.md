# Architecture — Knowledge Snapshot
> Останнє оновлення: Epic 7 In Progress (Data Scale).

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
  Frontend / Consumers   ← Epic 6 ✅ (React/Vite/TypeScript)
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
  SQLite (dev) → PostgreSQL (Epic 11)
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
| `rebuild_hero_stats.py` | Batch job: hero_stats_computed (з Python rollups) |
| `rebuild_item_builds.py` | Batch job: hero_item_build_computed |
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
| `analytics/matchup.py` | MatchupRepository (counter + synergy matrix reads, Epic 5) |

---

## Таблиці БД

### Raw data
| Таблиця | PK | Що зберігає | Стан |
|---------|----|-------------|------|
| `matches` | `id` | match_id, duration, radiant_win, start_time, patch, region | ✅ заповнюються з API |
| `players` | `id` (autoincrement) | account_id | |
| `match_players` | `(match_id, player_slot)` | hero_id, kills, deaths, assists, gpm, xpm, win, lane_role, is_roaming | ⚠️ lane_role NULL — матч не парсений OpenDota |
| `match_player_items` | `(match_id, player_slot, slot)` | item_id (slots 0-5) | |
| `ingestion_log` | `match_id` | status, ingested_at, error | |
| `heroes` | `id` | name, localized_name, primary_attr, attack_type | 127 героїв |
| `items` | `id` | name, localized_name, cost, flags | 470 items |
| `hero_role_scores` | `hero_id` | pos1-5, flex_score, primary_pos | 126/127 (Grimstroke gap) |

### Pre-computed (Epic 5)
| Таблиця | PK | Що зберігає | Особливості |
|---------|----|-------------|------------|
| `hero_stats_computed` | `id` | winrate, KDA, GPM по hero+pos+patch+region | UNIQUE з COALESCE(-1); rollups (NULL patch/region) |
| `hero_item_build_computed` | `(hero_id, primary_pos, item_id)` | times_bought, times_won | |
| `hero_matchup_computed` | `(hero_id, opponent_id)` | matches, wins (обидва напрямки) | is_radiant = player_slot < 128 |
| `hero_synergy_computed` | `(hero_id, ally_id)` | matches, wins | hero_id < ally_id завжди |

---

## API endpoints

### Epic 4 (raw queries)
```
GET /heroes/{id}/stats
GET /heroes/{id}/stats/role/{pos}
GET /heroes/{id}/items
GET /analytics/meta
GET /analytics/leaderboard/{pos}
GET /analytics/hero/{id}/timeline
```

### Epic 5 (pre-computed)
```
POST /computed/rebuild
GET  /computed/staleness
GET  /computed/heroes/{id}/stats
GET  /computed/heroes/top
GET  /computed/heroes/{id}/items/{pos}
GET  /computed/heroes/{id}/matchups    ← Task 5.9 (реалізовано в frontend, endpoint pending)
GET  /computed/heroes/{id}/synergies   ← Task 5.9
GET  /computed/heroes/{id}/counters    ← Task 5.9
```

---

## OpenDota Explorer API — відомі обмеження

> Перевірено 2026-03. Може змінитись при оновленні OpenDota.

| Колонка | Статус | Примітка |
|---------|--------|---------|
| `match_id` | ✅ | |
| `lobby_type` | ✅ | 7 = ranked |
| `avg_rank_tier` | ✅ | Замінила `avg_mmr` |
| `start_time` | ✅ | |
| `avg_mmr` | ❌ Видалена | Замінено на `avg_rank_tier` |
| `patch` | ❌ Видалена | Фільтрація по патчу неможлива через Explorer |
| `region` | ❌ Видалена | Фільтрація по регіону неможлива через Explorer |

**Rank Tier шкала:**
`10`=Herald · `20`=Guardian · `30`=Crusader · `40`=Archon
`50`=Legend · `60`=Ancient · `70`=Divine · `80+`=Immortal

---

## Pre-computed rebuild flow

```
Runner.run_cycle()
    → ingest N matches
    → if ingested > 0 and AUTO_REBUILD_AFTER_INGEST:
        → rebuild_hero_stats()
        → rebuild_item_builds()
        → rebuild_matchups()
        → rebuild_synergies()
```

---

## Відомі gaps

| Gap | Стан | Пріоритет | Epic |
|-----|------|-----------|------|
| `lane_role` / `is_roaming` NULL | Матч не парсений OpenDota | 🟡 | 7.4 |
| `player_slot` всі radiant | Деякі матчі не мають dire гравців | 🔴 | 7.3 |
| matchup/synergy endpoints | 5.9 не реалізовано | 🔴 | 5.9 |
| Grimstroke без role scores | HERO_META gap | 🟡 | — |
| Backpack items (slots 6-8) | Не збираємо | 🟢 | 7.7 |
| PostgreSQL migration | — | ⏳ | 11.1 |
| Docker Compose | — | ⏳ | 11.2 |

---

## Змінні середовища (актуальні)

```
OPENDOTA_BASE_URL, OPENDOTA_RATE_LIMIT, OPENDOTA_TIMEOUT, OPENDOTA_RETRIES
DISCOVERY_LOBBY_TYPE, DISCOVERY_MIN_RANK_TIER (замінив DISCOVERY_MIN_MMR)
DISCOVERY_LIMIT, DISCOVERY_INTERVAL_SEC
DB_PATH, LOG_LEVEL, AUTO_REBUILD_AFTER_INGEST, CORS_ORIGINS
```

---

## Версії технологій

```
Python 3.11+
FastAPI 0.115 + Uvicorn 0.29
Pydantic v2.12 + pydantic-settings 2.2
React 19 + Vite 7 + TypeScript 5
SQLite (dev) → PostgreSQL (Epic 11)
httpx 0.27 + requests 2.31
pytest 9.0 + pytest-asyncio
ruff 0.2 + mypy 1.8
GitHub Actions CI
```