# Dota 2 Analytics Pipeline — Roadmap
> Останнє оновлення: Epic 7 In Progress (Data Scale).

## Легенда статусів
✅ Done | 🔜 Next | 🔄 In Progress | ⏳ Backlog

---

## 🧱 Epic 1 — Ingestion Service MVP ✅
| Task | Опис | Статус |
|------|------|--------|
| 1.1 | Repo bootstrap: структура, CI, health endpoint | ✅ |
| 1.2 | Config: pydantic-settings, ENV | ✅ |
| 1.3 | Provider: HTTP client, rate limit, retry/backoff | ✅ |
| 1.4 | Domain DTO: Match, PlayerMatchStats, pydantic validation | ✅ |
| 1.5 | Persistence: SQLite repositories, UnitOfWork | ✅ |
| 1.6 | Orchestration: ingest pipeline, logging, smoke tests | ✅ |

---

## 🔍 Epic 2 — Match Discovery Service ✅
| Task | Опис | Статус |
|------|------|--------|
| 2.1 | Match Discovery query через OpenDota Explorer API | ✅ |
| 2.2 | Scheduler / runner: periodичний запуск | ✅ |
| 2.3 | Deduplication & state: ingestion_log | ✅ |
| 2.4 | Observability: structured logs, error tracking | ✅ |
| 2.5 | Integration & E2E: повний flow discovery → збережений матч | ✅ |

---

## 🧩 Epic 3 — Domain Model (Heroes, Items, Roles) ✅
| Task | Опис | Статус |
|------|------|--------|
| 3.1 | Hero domain model: heroes table, HeroRepository, sync | ✅ |
| 3.2 | Item domain model: items table, ItemRepository, sync | ✅ |
| 3.3 | Role taxonomy: Role enum, hero_role_scores | ✅ |
| 3.4 | Hero stats enrichment: EnrichedPlayerStats, enrich_match() | ✅ |
| 3.5 | Integration & E2E: sync → enrich → assert | ✅ |

---

## 📊 Epic 4 — Analytics Engine ✅
| Task | Опис | Статус |
|------|------|--------|
| 4.1 | HeroStatsRepository: winrate/pickrate/KDA | ✅ |
| 4.2 | Hero performance by role (primary_pos) | ✅ |
| 4.3 | Item build popularity: pickrate, win_pickrate | ✅ |
| 4.4 | Match timeline: early/mid/late + meta snapshot | ✅ |
| 4.5 | Analytics API endpoints (6 endpoints) | ✅ |
| 4.6 | E2E tests: повний цикл sync → analytics | ✅ |

---

## 🔧 Epic R1 — Project Health, Refactor & Audit ✅
| Task | Опис | Статус |
|------|------|--------|
| R1.1 | Repository refactor: розбити по сутностях | ✅ |
| R1.2 | Documentation update | ✅ |
| R1.3 | Business Logic Audit | ✅ |
| R1.4 | Real API Smoke Test (127 heroes, 470 items, 1 real match) | ✅ |

**Результат R1.4:** patch=59, region=3 заповнюються; lane_role NULL (очікувано);
Grimstroke gap в HERO_META (⚠️ відомо, низький пріоритет).

---

## 🏗 Epic 5 — Pre-computed Data Layer ✅
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
| 5.9 | MatchupRepository + matchup/synergy API endpoints | 🔜 |

**⚠️ 5.9 відкритий таск:** batch jobs і repository для matchup/synergy є,
але API endpoints (`GET /computed/heroes/{id}/matchups`, `GET /computed/heroes/{id}/synergies`) — не реалізовані.

---

## 🌐 Epic 6 — Frontend (React) 🔜

Окремий сервіс `services/frontend/`. React + Vite + TypeScript.
Backend повністю готовий. Frontend читає з `/computed` endpoints.

**MVP сторінки:**
- Hero Stats page — таблиця всіх героїв з winrate/KDA
- Hero Detail page — stats + item build + matchups/synergy
- Meta Snapshot page — leaderboard по позиціях
- Counter Picks page — counter та synergy matrix (після 5.9)

| Task | Опис | Статус |
|------|------|--------|
| 6.1 | Bootstrap: React + Vite + TypeScript + ESLint | ⏳ |
| 6.2 | API client layer (TypeScript types з OpenAPI /openapi.json) | ⏳ |
| 6.3 | Hero Stats page | ⏳ |
| 6.4 | Hero Detail page (stats + items) | ⏳ |
| 6.5 | Meta Snapshot page | ⏳ |
| 6.6 | CORS config на backend | ⏳ |
| 6.7 | Counter Picks / Synergy page | ⏳ |


---

## ✅ Epic 1 — Ingestion Service MVP
## ✅ Epic 2 — Match Discovery Service
## ✅ Epic 3 — Domain Model (Heroes, Items, Roles)
## ✅ Epic 4 — Analytics Engine
## ✅ Epic R1 — Project Health, Refactor & Audit
## ✅ Epic 5 — Pre-computed Data Layer
## ✅ Epic 6 — Frontend (React + Vite + TypeScript)

> Деталі епіків 1-6 збережені в git history. Нижче — активні та майбутні епіки.

---

## 🔄 Epic 7 — Data Scale & Quality

> Мета: 500+ матчів, реальні matchup/synergy дані, фікс відомих багів інгесту.
> Branch: `feat/epic-7-data-scale`

| Task | Опис | Статус |
|------|------|--------|
| 7.1 | Фікс Runner: `avg_mmr` → `avg_rank_tier` в Explorer query | ✅ |
| 7.2 | Scripts: `batch_ingest.py` і `discover_and_ingest.py` + `scripts/README.md` | ✅ |
| 7.3 | Дослідити `player_slot` issue — чому matchup_rows=0 | 🔜 |
| 7.4 | Додати `lane_role` + `is_roaming` в `match_players` (adapter + schema) | ⏳ |
| 7.5 | Фікс `rebuild_synergies` FK через FastAPI (UnitOfWork isolation) | ⏳ |
| 7.6 | Додати `net_worth`, `hero_damage`, `last_hits` в `match_players` | ⏳ |
| 7.7 | Backpack items (slots 6-8) + neutral slot | ⏳ |
| 7.8 | Smoke test: перевірити matchups і synergies з реальними даними | ⏳ |
| 7.9 | Тести для batch_ingest і нових полів | ⏳ |

**Acceptance criteria:**
- Runner знаходить матчі автоматично (avg_rank_tier працює)
- 500+ матчів в БД
- matchup_rows > 0 після rebuild
- `lane_role` не NULL для більшості гравців

---

## ⏳ Epic 8 — Match Analysis Service

> Новий сервіс `services/analysis/`. Watchlist матчів + аналіз якості драфту і гри.

| Task | Опис | Пріоритет |
|------|------|-----------|
| 8.1 | Bootstrap: `services/analysis/` — FastAPI + SQLite + структура | 🔴 |
| 8.2 | Watchlist API: `POST /watchlist/matches`, `GET /watchlist/matches` | 🔴 |
| 8.3 | Auto-fetch: при додаванні в watchlist — фетчити деталі з OpenDota | 🔴 |
| 8.4 | Match Report: `GET /watchlist/matches/{id}/report` | 🔴 |
| 8.5 | Draft quality score: synergy + counter balance | 🟠 |
| 8.6 | Economy analysis: GPM curves, net_worth | 🟠 |
| 8.7 | Teamfight efficiency: kills/deaths по фазах | 🟡 |
| 8.8 | Frontend: Watch List сторінка + Match Report | 🟠 |
| 8.9 | Тести: watchlist CRUD, report generation | 🔴 |

---

## ⏳ Epic 9 — Draft Assistant

> Rule-based рекомендації на основі matchup/synergy даних.

| Task | Опис | Пріоритет |
|------|------|-----------|
| 9.1 | Draft session API: `POST /draft/session`, `PATCH /draft/session/{id}` | 🔴 |
| 9.2 | Recommendation engine: score = synergy + counter + winrate | 🔴 |
| 9.3 | `GET /draft/session/{id}/recommendations` | 🔴 |
| 9.4 | Position awareness: рекомендує з урахуванням незаповнених позицій | 🟠 |
| 9.5 | Ban suggestions | 🟠 |
| 9.6 | Frontend: Draft Board UI | 🔴 |
| 9.7 | Тести: recommendation logic, edge cases | 🔴 |

---

## ⏳ Epic 10 — Team Builder

> Оптимальний склад команди проти конкретного противника.

| Task | Опис | Пріоритет |
|------|------|-----------|
| 10.1 | `POST /team-builder/optimize` → input: вороги, output: оптимальна команда | 🔴 |
| 10.2 | Optimization: комбінаторний пошук з евристикою | 🔴 |
| 10.3 | Score breakdown по кожному герою | 🟠 |
| 10.4 | Frontend: Team Builder UI | 🟠 |
| 10.5 | Тести: optimizer correctness, performance | 🔴 |

---

## ⏳ Epic 11 — Scale & Production

| Task | Опис | Пріоритет |
|------|------|-----------|
| 11.1 | PostgreSQL migration (Alembic) | 🔴 |
| 11.2 | Docker Compose: ingestion + analysis + frontend + postgres | 🔴 |
| 11.3 | Pagination для всіх list endpoints | 🟠 |
| 11.4 | Response caching (Redis або in-memory) | 🟠 |
| 11.5 | Rate limiting для публічних endpoints | 🟠 |
| 11.6 | Structured logging + Prometheus | 🟡 |
| 11.7 | GitHub Actions: deploy pipeline | 🟡 |

---

## Послідовність

```
✅1→2→3→4→R1→5→6 → 🔄7 → ⏳8 → ⏳9 → ⏳10 → ⏳11
```

## Версії

```
v1.1.0 — Epic 6 done (Frontend)
v1.2.0 — Epic 7 done (Data Scale)      ← поточна мета
v2.0.0 — Epic 9 done (Draft Assistant)
v3.0.0 — Epic 11 done (Production)
```

## Commit convention

```
feat(7.3): investigate player_slot radiant-only issue
fix(7.5): rebuild_synergies FK isolation in FastAPI
feat(8.1): bootstrap analysis service
```

## Issue naming

```
[EPIC-X][TASK-X.Y] Short description
[EPIC-6][TASK-6.1] Bootstrap React + Vite + TypeScript
[EPIC-5][TASK-5.9] Matchup/synergy API endpoints
```