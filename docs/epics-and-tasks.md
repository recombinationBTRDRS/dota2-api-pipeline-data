# Dota 2 Analytics Pipeline — Roadmap
> Останнє оновлення: після Epic 5 + R1 Done.

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

## 🧠 Epic 7 — Recommendation Engine ⏳
| Task | Опис | Статус |
|------|------|--------|
| 7.1 | Rule-based recommendations (по pre-computed stats) | ⏳ |
| 7.2 | Counter picks з hero_matchup_computed | ⏳ |
| 7.3 | Synergy picks з hero_synergy_computed | ⏳ |
| 7.4 | Draft analyzer: heroes picked → оцінка + рекомендації | ⏳ |

---

## 🚀 Epic 8 — Public API & Scale ⏳
| Task | Опис | Статус |
|------|------|--------|
| 8.1 | Pagination і filters для всіх list endpoints | ⏳ |
| 8.2 | Response caching (in-memory / Redis) | ⏳ |
| 8.3 | Rate limiting для публічних endpoints | ⏳ |
| 8.4 | PostgreSQL migration (Alembic) | ⏳ |
| 8.5 | Docker Compose: app + db + worker | ⏳ |
| 8.6 | Monitoring: structured logs, Prometheus | ⏳ |

---

## Послідовність

```
✅1 → ✅2 → ✅3 → ✅4 → ✅R1 → ✅5 → 🔜6(Frontend) → 7(Recommendations) → 8(Scale)
```

---

## Commit convention

```
feat | fix | test | refactor | docs | chore
feat(6.1): bootstrap React + Vite + TypeScript
feat(5.9): matchup/synergy API endpoints
docs(R1.2): update architecture snapshot
```

## Issue naming

```
[EPIC-X][TASK-X.Y] Short description
[EPIC-6][TASK-6.1] Bootstrap React + Vite + TypeScript
[EPIC-5][TASK-5.9] Matchup/synergy API endpoints
```