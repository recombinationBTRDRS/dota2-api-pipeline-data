# Dota 2 Analytics Pipeline — Roadmap
> Останнє оновлення: Epic 7 Done (Data Scale & Quality). Epic 8 In Progress.

## Легенда статусів
✅ Done | 🔄 In Progress | 🔜 Next | ⏳ Backlog

---

## ✅ Epic 1 — Ingestion Service MVP
| Task | Опис | Статус |
|------|------|--------|
| 1.1 | Repo bootstrap: структура, CI, health endpoint | ✅ |
| 1.2 | Config: pydantic-settings, ENV | ✅ |
| 1.3 | Provider: HTTP client, rate limit, retry/backoff | ✅ |
| 1.4 | Domain DTO: Match, PlayerMatchStats, pydantic validation | ✅ |
| 1.5 | Persistence: SQLite repositories, UnitOfWork | ✅ |
| 1.6 | Orchestration: ingest pipeline, logging, smoke tests | ✅ |

---

## ✅ Epic 2 — Match Discovery Service
| Task | Опис | Статус |
|------|------|--------|
| 2.1 | Match Discovery query через OpenDota Explorer API | ✅ |
| 2.2 | Scheduler / runner: periodичний запуск | ✅ |
| 2.3 | Deduplication & state: ingestion_log | ✅ |
| 2.4 | Observability: structured logs, error tracking | ✅ |
| 2.5 | Integration & E2E: повний flow discovery → збережений матч | ✅ |

---

## ✅ Epic 3 — Domain Model (Heroes, Items, Roles)
| Task | Опис | Статус |
|------|------|--------|
| 3.1 | Hero domain model: heroes table, HeroRepository, sync | ✅ |
| 3.2 | Item domain model: items table, ItemRepository, sync | ✅ |
| 3.3 | Role taxonomy: Role enum, hero_role_scores | ✅ |
| 3.4 | Hero stats enrichment: EnrichedPlayerStats, enrich_match() | ✅ |
| 3.5 | Integration & E2E: sync → enrich → assert | ✅ |

---

## ✅ Epic 4 — Analytics Engine
| Task | Опис | Статус |
|------|------|--------|
| 4.1 | HeroStatsRepository: winrate/pickrate/KDA | ✅ |
| 4.2 | Hero performance by role (primary_pos) | ✅ |
| 4.3 | Item build popularity: pickrate, win_pickrate | ✅ |
| 4.4 | Match timeline: early/mid/late + meta snapshot | ✅ |
| 4.5 | Analytics API endpoints (6 endpoints) | ✅ |
| 4.6 | E2E tests: повний цикл sync → analytics | ✅ |

---

## ✅ Epic R1 — Project Health, Refactor & Audit
| Task | Опис | Статус |
|------|------|--------|
| R1.1 | Repository refactor: розбити по сутностях | ✅ |
| R1.2 | Documentation update | ✅ |
| R1.3 | Business Logic Audit | ✅ |
| R1.4 | Real API Smoke Test (127 heroes, 470 items, реальний матч) | ✅ |

---

## ✅ Epic 5 — Pre-computed Data Layer
| Task | Опис | Статус |
|------|------|--------|
| 5.1 | Schema: hero_stats_computed, hero_item_build_computed, matchup, synergy | ✅ |
| 5.2 | Batch job: rebuild_hero_stats (Python rollups для NULL patch/region) | ✅ |
| 5.3 | Batch job: rebuild_item_builds | ✅ |
| 5.4 | Batch job: rebuild_matchups (counter matrix, обидва напрямки) | ✅ |
| 5.5 | Batch job: rebuild_synergies (hero_id < ally_id) | ✅ |
| 5.6 | Scheduler: AUTO_REBUILD_AFTER_INGEST в runner | ✅ |
| 5.7 | ComputedStatsRepository + /computed endpoints | ✅ |
| 5.8 | E2E tests: rebuild → API → assert | ✅ |
| 5.9 | MatchupRepository + matchup/synergy/counter API endpoints | ✅ |

---

## ✅ Epic 6 — Frontend (React + Vite + TypeScript)
| Task | Опис | Статус |
|------|------|--------|
| 6.1 | Bootstrap: React 19 + Vite 7 + TypeScript 5 | ✅ |
| 6.2 | API client layer: apiFetch wrapper, TypeScript типи | ✅ |
| 6.3 | Hero Stats page: таблиця, фільтр по позиції, сортування | ✅ |
| 6.4 | Hero Detail page: stats + items + matchups + synergies | ✅ |
| 6.5 | Meta Snapshot page: 5 колонок по позиціях | ✅ |
| 6.6 | CORS middleware на backend + config CORS_ORIGINS | ✅ |
| 6.7 | Counter/Synergy в Hero Detail | ✅ |
| 6.x | CodeRabbit fixes: a11y, NaN guard, network errors | ✅ |

---

## ✅ Epic 7 — Data Scale & Quality
> Мета: 500+ матчів, реальні matchup/synergy дані, фікс відомих багів інгесту.
> Branch: `feat/epic-7-data-scale` → merged → `v1.2.0`

| Task | Опис | Статус |
|------|------|--------|
| 7.1 | Фікс Runner: `avg_mmr` → `avg_rank_tier` в Explorer query | ✅ |
| 7.2 | Scripts: `batch_ingest.py`, `discover_and_ingest.py` + README | ✅ |
| 7.3 | Фікс `player_slot`: preserve raw API value (0-4 radiant, 128-132 dire) | ✅ |
| 7.4 | Додати `lane_role` + `is_roaming` в `match_players` | ✅ |
| 7.5 | Фікс `rebuild_synergies` FK (heroes sync перед rebuild) | ✅ |
| 7.6 | Додати `net_worth`, `hero_damage`, `tower_damage`, `hero_healing`, `last_hits` | ✅ |
| 7.8 | Smoke test: matchups, synergies, player_slot, performance fields | ✅ |
| 7.9 | `discover_and_ingest.py`: `--days` і `--before-match` фільтри | ✅ |

**Результат Epic 7:**
- `player_slot` raw: radiant=5/dire=5 ✅
- `matchup_rows=7228`, `synergy_rows=3095` з 200+ матчів ✅
- `net_worth`, `hero_damage`, `last_hits` заповнюються ✅
- Discovery по часовому фільтру (--days, --before-match) ✅

---

## 🔄 Epic 8 — Match Analysis Service
> Окремий мікросервіс `services/analysis/` на FastAPI + SQLite.
> Аналізує конкретні матчі: draft quality, economy, teamfight efficiency.
> Читає pre-computed дані з Ingestion сервісу через HTTP або shared DB.
> Branch: `feat/epic-8`

### Архітектура сервісу
```
services/analysis/
├── app/
│   ├── main.py              ← FastAPI, /health
│   ├── config.py            ← ENV: INGESTION_API_URL, DB_PATH
│   ├── routers/
│   │   ├── watchlist.py     ← /watchlist endpoints
│   │   └── reports.py       ← /reports endpoints
│   ├── analyzers/
│   │   ├── draft.py         ← DraftAnalyzer: synergy + counter score
│   │   ├── economy.py       ← EconomyAnalyzer: GPM/net_worth vs норма
│   │   └── teamfight.py     ← TeamfightAnalyzer: kills/deaths по фазах
│   └── clients/
│       └── ingestion.py     ← HTTP client до Ingestion API
├── db/
│   ├── schema.sql           ← watchlist table
│   ├── sqlite.py
│   └── repositories/
│       └── watchlist.py
├── domains/
│   └── reports/
│       └── dtos.py          ← MatchReport, DraftScore, EconomySnapshot
└── tests/
    ├── test_watchlist.py
    ├── test_draft_analyzer.py
    └── test_economy_analyzer.py
```

| Task | Опис | Статус |
|------|------|--------|
| 8.1 | Bootstrap: `services/analysis/` — FastAPI + SQLite + структура + /health | 🔜 |
| 8.2 | Watchlist DB: `watchlist` таблиця, WatchlistRepository, CRUD | 🔜 |
| 8.3 | Watchlist API: `POST /watchlist/matches`, `GET /watchlist/matches`, `DELETE /watchlist/matches/{id}` | 🔜 |
| 8.4 | Ingestion client: HTTP клієнт для читання matchup/synergy даних з Ingestion API | 🔜 |
| 8.5 | DraftAnalyzer: synergy score своєї команди + counter score проти ворогів | 🔜 |
| 8.6 | EconomyAnalyzer: net_worth/GPM гравців vs середнє по герою з БД | 🔜 |
| 8.7 | TeamfightAnalyzer: kills/deaths розбивка по early/mid/late фазах | ⏳ |
| 8.8 | Match Report API: `POST /reports/matches/{id}` → генерує і кешує звіт | 🔜 |
| 8.9 | `GET /reports/matches/{id}` → повертає збережений звіт | 🔜 |
| 8.10 | Frontend: "Analyze Match" сторінка — ввів match_id → отримав звіт | ⏳ |
| 8.11 | Тести: watchlist CRUD, DraftAnalyzer, EconomyAnalyzer unit tests | 🔜 |
| 8.12 | Smoke test: реальний match_id → повний report | 🔜 |

**Acceptance criteria Epic 8:**
- `POST /watchlist/matches` приймає match_id, зберігає в watchlist
- `POST /reports/matches/{id}` повертає JSON з draft_score, economy, teamfight
- `draft_score` рахується через matchup/synergy з Ingestion pre-computed
- `economy` порівнює net_worth/GPM з середнім значенням по герою в БД
- Всі тести проходять, smoke test green

---

## ⏳ Epic 9 — Draft Assistant
> Rule-based рекомендації на основі pre-computed matchup/synergy даних.

| Task | Опис | Пріоритет |
|------|------|-----------|
| 9.1 | Draft state API: `POST /draft/session`, `PATCH /draft/session/{id}` | 🔴 |
| 9.2 | Recommendation engine: score = synergy + counter + winrate | 🔴 |
| 9.3 | Score formula + `GET /draft/session/{id}/recommendations` | 🔴 |
| 9.4 | Position awareness: рекомендує з урахуванням незаповнених позицій | 🟠 |
| 9.5 | Ban suggestions | 🟠 |
| 9.6 | Frontend: Draft Board UI | 🔴 |
| 9.7 | Тести: recommendation logic, edge cases | 🔴 |

**Acceptance criteria:** вибрав 3 своїх + 2 ворогів → система рекомендує 5 найкращих варіантів з поясненням score.

---

## ⏳ Epic 10 — Team Builder
> Оптимальний склад команди проти конкретного противника.

| Task | Опис | Пріоритет |
|------|------|-----------|
| 10.1 | `POST /team-builder/optimize` → input: вороги, output: оптимальна команда | 🔴 |
| 10.2 | Optimization: комбінаторний пошук з евристикою (< 1s для 127 героїв) | 🔴 |
| 10.3 | Constraints: один герой на позицію, без повторів | 🔴 |
| 10.4 | Score breakdown по кожному герою | 🟠 |
| 10.5 | Frontend: Team Builder UI | 🟠 |
| 10.6 | Тести: optimizer correctness + performance | 🔴 |

---

## ⏳ Epic 11 — Scale & Production
> PostgreSQL, Docker Compose, monitoring.

| Task | Опис | Пріоритет |
|------|------|-----------|
| 11.1 | PostgreSQL migration (Alembic) для Ingestion сервісу | 🔴 |
| 11.2 | Docker Compose: ingestion + analysis + frontend + postgres | 🔴 |
| 11.3 | Pagination для всіх list endpoints | 🟠 |
| 11.4 | Response caching (Redis або in-memory) | 🟠 |
| 11.5 | Rate limiting для публічних endpoints | 🟠 |
| 11.6 | Structured logging + Prometheus metrics | 🟡 |
| 11.7 | GitHub Actions: deploy pipeline | 🟡 |

---

## Мікросервісна архітектура (цільова)

```
OpenDota API
    │
    ▼
services/ingestion/          ← Epic 1-7: збір, нормалізація, pre-computed
    │  FastAPI :8000
    │  SQLite → PostgreSQL (Epic 11)
    │
    ├─ /heroes, /matches, /analytics, /computed
    │
    ▼
services/analysis/           ← Epic 8: аналіз конкретних матчів
    │  FastAPI :8001
    │  SQLite (watchlist + reports)
    │  Читає з Ingestion API або shared DB
    │
    ├─ /watchlist, /reports
    │
    ▼
services/frontend/           ← Epic 6: React + Vite
    │  Vite :5173
    │
    └─ читає з :8000 і :8001
```

---

## Послідовність

```
✅1→2→3→4→R1→5→6→7 → 🔄8 → ⏳9 → ⏳10 → ⏳11
```

## Версії

```
v1.0.0 — Epic 5 done (Pre-computed Layer)
v1.1.0 — Epic 6 done (Frontend)
v1.2.0 — Epic 7 done (Data Scale)       ✅ tagged
v1.3.0 — Epic 8 done (Match Analysis)   ← поточна мета
v2.0.0 — Epic 9 done (Draft Assistant)
v3.0.0 — Epic 11 done (Production)
```

## Commit convention

```
feat(8.1): bootstrap analysis service
feat(8.5): DraftAnalyzer synergy + counter score
fix(8.4): ingestion client timeout handling
test(8.11): watchlist CRUD + analyzer unit tests
```

## Issue naming

```
[EPIC-8][TASK-8.1] Bootstrap analysis service
[EPIC-8][TASK-8.5] DraftAnalyzer: synergy + counter score
[EPIC-9][TASK-9.1] Draft session API
```