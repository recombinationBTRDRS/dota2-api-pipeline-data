# High-Level Plan — Dota 2 Analytics Pipeline
> Останнє оновлення: після Epic 5 Done + R1.4 Smoke Test passed.

---

## Бачення продукту

Платформа для аналізу Dota 2 яка:
1. **Збирає** матчі з OpenDota API (raw data)
2. **Нормалізує** і будує **pre-computed таблиці** — "золоті дані" по героях, items, ролях, counter-picks
3. **Зберігає** ці таблиці як власний ресурс (не залежний від uptime зовнішніх API)
4. **Видає** аналітику, гайди, рекомендації через API → фронтенд

**Ключова ідея:** сирі матчі — тимчасові. Pre-computed таблиці — бізнес-актив.

---

## Фази

### Phase 1 — Foundation ✅
- Репозиторій, CI/CD, базова структура
- Config, ENV, health endpoint
- DB схема, DTO для OpenDota JSON

### Phase 2 — Data Pipeline ✅
- Match Discovery (filters, scheduler)
- Ingestion (API client, retry, rate limit)
- Normalization (JSON → DTO → DB)
- Domain model (Heroes, Items, Roles)

### Phase 3 — Analytics Engine ✅
- Hero stats: winrate, pickrate, KDA
- Performance by role
- Item build popularity
- Match timeline (early/mid/late)
- Meta snapshot (winrate × pickrate)
- Analytics API endpoints

### Phase 4 — Project Health & Refactor ✅
- Repository refactor по сутностях
- Business Logic Audit
- Real API smoke test (✅ 127 heroes, 470 items, реальний матч)

### Phase 5 — Pre-computed Data Layer ✅
- hero_stats_computed (з Python rollups по patch/region/NULL)
- hero_item_build_computed
- hero_matchup_computed (counter matrix)
- hero_synergy_computed (synergy matrix)
- Auto-rebuild scheduler
- Computed API endpoints
- **Pending 5.9:** matchup/synergy API endpoints

### Phase 6 — Frontend (React) 🔜
- Окремий сервіс `services/frontend/`
- React + Vite + TypeScript
- Читає з `/computed` endpoints
- Hero Stats, Hero Detail, Meta Snapshot, Counter Picks

### Phase 7 — Recommendation Engine ⏳
- Rule-based рекомендації по pre-computed stats
- Counter picks, synergy picks
- Draft analyzer

### Phase 8 — Public API & Scale ⏳
- Pagination, caching, rate limiting
- PostgreSQL migration (Alembic)
- Docker Compose
- Monitoring

---

## Принципи архітектури

```
External APIs → Raw Ingestion → Normalization
                                      ↓
                            Pre-computed Tables  ← batch jobs
                                      ↓
                            Analytics API  →  Frontend (React)
```

- Шари ізольовані: db не знає про domains і providers
- Pre-computed = batch rebuild, не real-time
- SQLite (dev) → PostgreSQL (prod, Epic 8)
- Versioning: API v1.0.0

---

## Версія

```
v0.x — Epics 1-4 (Foundation + Data Pipeline + Analytics)
v1.0.0 — Epic 5 done (Pre-computed Layer повністю готовий)
v1.x — Epic 6 (Frontend)
v2.0.0 — Epic 7 (Recommendations)
```