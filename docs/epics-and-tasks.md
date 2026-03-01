# Dota 2 Analytics Pipeline — Roadmap

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
| 3.3 | Role taxonomy: Role enum, hero_role_scores, HeroRoleScoreRepository | ✅ |
| 3.4 | Hero stats enrichment: EnrichedPlayerStats, enrich_match() | ✅ |
| 3.5 | Integration & E2E: sync → enrich → assert | ✅ |

**Ключові рішення:**
- `HERO_META` — статичні бали pos1-5 по імені (125 героїв, вшито в код)
- `primary_pos → Role` маппінг в `app/enrich.py` — ізоляція шарів

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

**Analytics endpoints:**
```
GET /heroes/{id}/stats
GET /heroes/{id}/stats/role/{pos}
GET /heroes/{id}/items
GET /analytics/meta
GET /analytics/leaderboard/{pos}
GET /analytics/hero/{id}/timeline
```

---

## 🔧 Epic R1 — Project Health, Refactor & Audit 🔜

Ціль: привести проект до порядку перед великими змінами.
Три напрямки: рефактор коду, аудит логіки, перевірка на реальних даних.

### R1.1 — Repository Refactor

Розбити `db/repositories.py` (~800 рядків, 11 класів) по сутностях.

**Цільова структура:**
```
db/
└── repositories/
    ├── __init__.py      ← re-export всього (зворотна сумісність)
    ├── base.py          ← constants (_MAX_ERROR_LEN, phase thresholds)
    ├── matches.py       ← Match, MatchPlayer, MatchPlayerItem, IngestionLog
    ├── heroes.py        ← Hero, HeroRoleScore
    ├── items.py         ← Item
    ├── players.py       ← Player
    └── analytics/
        ├── __init__.py
        ├── hero_stats.py   ← HeroStatsRepository + rows (4.1, 4.2)
        ├── item_build.py   ← ItemBuildRepository + ItemBuildEntry (4.3)
        └── timeline.py     ← MatchTimelineRepository + rows (4.4)
```

| Task | Опис | Статус |
|------|------|--------|
| R1.1a | Створити структуру `db/repositories/` | ⏳ |
| R1.1b | Перенести write repos (matches, heroes, items, players) | ⏳ |
| R1.1c | Перенести analytics repos в `analytics/` | ⏳ |
| R1.1d | `__init__.py` re-export — жоден import не ламається | ⏳ |
| R1.1e | Прогнати pytest — всі тести green | ⏳ |

### R1.2 — Documentation Update

Привести всю документацію до актуального стану.

| Task | Опис | Статус |
|------|------|--------|
| R1.2a | `docs/architecture.md` — knowledge snapshot (є, оновити) | ⏳ |
| R1.2b | `docs/epics-and-tasks.md` — цей файл | 🔄 |
| R1.2c | `docs/high-level-plan.md` — оновлена фазова карта | ⏳ |
| R1.2d | `README.md` — актуальний стан + нові endpoints | ⏳ |

### R1.3 — Business Logic Audit

Пройтись по всій логіці, зафіксувати рішення, виявити невідповідності.

**Що перевіряємо:**

| Питання | Поточний стан | Дія |
|---------|--------------|-----|
| `primary_pos` — статика чи реальна позиція? | Статична (HERO_META) | Рішення: додати `lane_role` з матчу? |
| `patch`, `region` в matches | Завжди NULL | Рішення: заповнювати? |
| `rank_tier`, `mmr` в players | Завжди NULL | Рішення: заповнювати? |
| Backpack items (slot 6-8) і neutral | Не збираємо | Рішення: додати? |
| `meta_score` формула | `winrate * pickrate * 100` | Правильна? |
| Phase thresholds (1800/3000s) | Захардкоджені | Перенести в config? |
| `HERO_META` оновлення | Вручну | Автоматичний sync? |
| `flex_score` поріг (3) | Захардкоджений | В config? |

| Task | Опис | Статус |
|------|------|--------|
| R1.3a | Аудит всіх NULL полів — рішення що збирати | ⏳ |
| R1.3b | primary_pos — реальна vs типова, impl якщо треба | ⏳ |
| R1.3c | Item slots — backpack і neutral | ⏳ |
| R1.3d | Константи → config (.env) | ⏳ |
| R1.3e | Analytics формули — перегляд і корекція | ⏳ |
| R1.3f | HERO_META стратегія оновлення | ⏳ |

### R1.4 — Real API Smoke Test

Перевірити що проект реально працює з OpenDota API, а не тільки з mock даними.

**Проблема:** всі наші тести — unit з mock або fake даними. Реальна поведінка API може відрізнятись.

| Task | Опис | Статус |
|------|------|--------|
| R1.4a | Запустити повний pipeline на реальних даних (10-20 матчів) | ⏳ |
| R1.4b | Перевірити що adapter коректно нормалізує всі поля | ⏳ |
| R1.4c | Перевірити що analytics endpoints повертають реальні цифри | ⏳ |
| R1.4d | Зафіксувати всі розбіжності між mock і реальними даними | ⏳ |
| R1.4e | Виправити що зламалось | ⏳ |

---

## 🏗 Epic 5 — Pre-computed Data Layer ⏳

Ціль: побудувати "золоті таблиці" — pre-computed агрегати що є основним бізнес-ресурсом платформи.

**Ключова ідея:**
- Сирі матчі (`match_players`) — тимчасовий raw матеріал
- Pre-computed таблиці — стабільний ресурс, не залежить від API
- Аналітика читає з pre-computed, не рахує по raw щоразу
- Batch job'и rebuild ці таблиці (раз на добу або по тригеру)

**Цільові таблиці:**

| Таблиця | Що містить | Granularity |
|---------|-----------|-------------|
| `hero_aggregated_stats` | winrate, pickrate, avg KDA по patch/region | hero + patch |
| `hero_role_aggregated_stats` | winrate по primary_pos | hero + pos |
| `hero_item_build_stats` | топ builds з win_pickrate | hero + pos |
| `hero_matchup_stats` | winrate A проти B (counter matrix) | hero_a + hero_b |
| `hero_synergy_stats` | winrate A разом з B | hero_a + hero_b |
| `item_effectiveness` | ефективність items в різних ситуаціях | item + context |

| Task | Опис | Статус |
|------|------|--------|
| 5.1 | Схема pre-computed таблиць + DDL | ⏳ |
| 5.2 | Batch job: rebuild `hero_aggregated_stats` | ⏳ |
| 5.3 | Batch job: rebuild `hero_item_build_stats` | ⏳ |
| 5.4 | Batch job: rebuild `hero_matchup_stats` (counter matrix) | ⏳ |
| 5.5 | Batch job: rebuild `hero_synergy_stats` | ⏳ |
| 5.6 | Scheduler: автоматичний rebuild (cron або тригер) | ⏳ |
| 5.7 | Analytics API перенести на pre-computed таблиці | ⏳ |
| 5.8 | E2E: ingest → rebuild → API → assert | ⏳ |

---

## 🌐 Epic 6 — Frontend (React) ⏳

Окремий сервіс `services/frontend/`.

**MVP сторінки:**
- Hero Stats — таблиця з winrate/pickrate/KDA
- Hero Detail — stats + item build + timeline
- Meta Snapshot — leaderboard по позиціях
- Hero Matchups — counter/synergy (після Epic 5)

| Task | Опис | Статус |
|------|------|--------|
| 6.1 | Bootstrap React + Vite + TypeScript | ⏳ |
| 6.2 | API client layer (types з OpenAPI spec) | ⏳ |
| 6.3 | Hero Stats page | ⏳ |
| 6.4 | Hero Detail page | ⏳ |
| 6.5 | Meta Snapshot page | ⏳ |
| 6.6 | CORS config на backend | ⏳ |

---

## 🧠 Epic 7 — Recommendation Engine ⏳

| Task | Опис | Статус |
|------|------|--------|
| 7.1 | Rule-based recommendations (по pre-computed stats) | ⏳ |
| 7.2 | Counter picks з `hero_matchup_stats` | ⏳ |
| 7.3 | Synergy picks з `hero_synergy_stats` | ⏳ |
| 7.4 | Draft analyzer: 10 героїв → оцінка + рекомендації | ⏳ |

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

## Послідовність епіків

```
✅1 → ✅2 → ✅3 → ✅4 → 🔜R1 → 5(Pre-computed) → 6(Frontend) → 7(Recommendations) → 8(Scale)
```

**Логіка послідовності:**
- **R1 перший** — рефактор + аудит + smoke test на реальних даних перш ніж будувати далі
- **5 (Pre-computed) другий** — визначає архітектуру даних, від якої залежить все далі
- **6 (Frontend) після 5** — буде читати з pre-computed, не з raw
- **7 після 5** — рекомендації на основі якісних даних

---

## Commit convention

```text
<type>(<scope>): <short description>

Types:   feat | fix | test | refactor | docs | chore
Scope:   epic-task number або module name

Examples:
  refactor(R1.1b): split write repos into matches.py and heroes.py
  feat(5.2): add batch job for hero_aggregated_stats rebuild
  docs(R1.2): update architecture snapshot
  test(R1.4): real API smoke test — 20 matches ingested
```

## Issue naming

```text
[EPIC-X][TASK-X.Y] Short description

Examples:
  [EPIC-R1][TASK-R1.1b] Split write repositories by entity
  [EPIC-R1][TASK-R1.3b] Decide on primary_pos: real lane_role vs static
  [EPIC-5][TASK-5.4] Build hero_matchup_stats counter matrix
```