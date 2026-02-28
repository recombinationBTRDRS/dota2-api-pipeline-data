# Dota 2 Analytics Pipeline — Roadmap

## Легенда статусів
✅ Done | 🔜 Next | 🔄 In Progress | ⏳ Backlog

---

## 🧱 Epic 1 — Ingestion Service MVP ✅

Ціль: production-ready сервіс для отримання, валідації та збереження матчів.

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

Ціль: автономний пошук матчів за фільтрами → передача в Ingestion.

| Task | Опис | Статус |
|------|------|--------|
| 2.1 | Match Discovery query через OpenDota Explorer API | ✅ |
| 2.2 | Scheduler / runner: periodичний запуск | ✅ |
| 2.3 | Deduplication & state: ingestion_log | ✅ |
| 2.4 | Observability: structured logs, error tracking | ✅ |
| 2.5 | Integration & E2E: повний flow discovery → збережений матч | ✅ |

---

## 🧩 Epic 3 — Domain Model (Heroes, Items, Roles) ✅

Ціль: нормалізована доменна модель для героїв, предметів і ролей.

| Task | Опис | Статус |
|------|------|--------|
| 3.1 | Hero domain model: heroes table, HeroRepository, sync | ✅ |
| 3.2 | Item domain model: items table, ItemRepository, sync | ✅ |
| 3.3 | Role taxonomy: Role enum, hero_role_scores table, HeroRoleScoreRepository | ✅ |
| 3.4 | Hero stats enrichment: EnrichedPlayerStats, enrich_match(), get_with_role() | ✅ |
| 3.5 | Integration & E2E: sync → enrich → assert, test_domain_model_cycle.py | ✅ |

**Ключові архітектурні рішення Epic 3:**
- `domains/heroes/meta.py` — universal HeroMeta (pos1-5) без hero_id
- `providers/opendota/hero_id_map.py` — adapter: name → opendota_id
- `enrich_match()` приймає HeroRepository як DI → легко тестується без DB

---

## 📊 Epic 4 — Analytics Engine 🔜

Ціль: SQL-запити і агрегація по матчах для статистики героїв і ролей.

| Task | Опис | Статус |
|------|------|--------|
| 4.1 | HeroStatsRepository: winrate і pickrate по hero_id | 🔜 |
| 4.2 | Hero performance by role: winrate з урахуванням primary_pos | ⏳ |
| 4.3 | Item build popularity: топ items per hero | ⏳ |
| 4.4 | Match timeline analysis: early/mid/late performance | ⏳ |
| 4.5 | Analytics API endpoints (FastAPI): /heroes/{id}/stats | ⏳ |
| 4.6 | Integration tests для всіх analytics queries | ⏳ |

**Залежності:** потребує заповнених match_players (Epic 1/2) і hero_role_scores (Epic 3).

---

## 🧠 Epic 5 — Recommendation Engine ⏳

Ціль: рекомендації героїв на основі драфту і статистики.

| Task | Опис | Статус |
|------|------|--------|
| 5.1 | Rule-based recommendations MVP: hero по ролі і meta score | ⏳ |
| 5.2 | Counter picks: які герої виграють проти конкретного hero | ⏳ |
| 5.3 | Synergy picks: які герої добре грають разом | ⏳ |
| 5.4 | Draft analyzer: 10 героїв → оцінка драфту | ⏳ |
| 5.5 | Win probability estimation по драфту | ⏳ |

**Залежності:** потребує Analytics Engine (Epic 4).

---

## 🌐 Epic 6 — Public API ⏳

Ціль: REST API готовий до підключення фронтенду.

| Task | Опис | Статус |
|------|------|--------|
| 6.1 | Public API endpoints: heroes, matches, stats | ⏳ |
| 6.2 | Filters & Pagination для всіх list endpoints | ⏳ |
| 6.3 | OpenAPI docs (автоматично через FastAPI) | ⏳ |
| 6.4 | Response caching (in-memory або Redis) | ⏳ |
| 6.5 | Rate limiting для публічних endpoints | ⏳ |

---

## 🚀 Epic 7 — Scale & Production ⏳

Ціль: перехід з SQLite dev → production-ready інфраструктура.

| Task | Опис | Статус |
|------|------|--------|
| 7.1 | PostgreSQL migration (Alembic) | ⏳ |
| 7.2 | Async ingestion pipeline (httpx + asyncio) | ⏳ |
| 7.3 | Celery / task queue для scheduled jobs | ⏳ |
| 7.4 | Docker Compose: app + db + worker | ⏳ |
| 7.5 | Monitoring: structured logs, metrics (Prometheus) | ⏳ |

---

## Commit convention

```
<type>(<scope>): <short description>

Types:   feat | fix | test | refactor | docs | chore
Scope:   epic-task number або module name

Examples:
  feat(3.4): add EnrichedPlayerStats and enrich_match()
  fix(3.3): move Role import to module level in repositories
  test(3.5): add E2E test for full domain model cycle
  docs(epic-3): update README status and architecture
  chore: update ruff config
```

## Issue naming convention

```
[EPIC-N][TASK-N.M] Short description

Examples:
  [EPIC-4][TASK-4.1] HeroStatsRepository: winrate and pickrate
  [EPIC-4][TASK-4.2] Hero performance by role
```