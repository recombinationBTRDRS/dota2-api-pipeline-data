# High-Level Plan — Dota 2 Analytics Pipeline
> Останнє оновлення: Epic 4 Done. Переломний момент перед Epic 5.

---

## Бачення продукту

Платформа для аналізу Dota 2 яка:
1. **Збирає** матчі з OpenDota API (raw data)
2. **Нормалізує** і будує **pre-computed таблиці** — "золоті дані" по героях, items, ролях
3. **Зберігає** ці таблиці як власний ресурс (не залежний від uptime зовнішніх API)
4. **Видає** аналітику, гайди, рекомендації через API → фронтенд

**Ключова ідея:** сирі матчі — тимчасові. Pre-computed таблиці — бізнес-актив.
Аналітика читає з pre-computed, не рахує по raw кожного разу.

---

## Фази

### Phase 1 — Foundation ✅
- Репозиторій, CI/CD, базова структура
- Config, ENV, health endpoint
- DB схема (ER)
- DTO для OpenDota JSON

### Phase 2 — Data Pipeline ✅
- Match Discovery (filters, scheduler)
- Ingestion (API client, retry, rate limit)
- Normalization (JSON → DTO → DB)
- Persistence (SQLite, repositories, UnitOfWork)
- Domain model (Heroes, Items, Roles)

### Phase 3 — Analytics Engine ✅
- Hero stats: winrate, pickrate, KDA
- Performance by role (primary_pos)
- Item build popularity
- Match timeline (early/mid/late)
- Meta snapshot (winrate × pickrate)
- Analytics API endpoints

### Phase 4 — Pre-computed Data Layer 🔜
Ціль: будувати "золоті таблиці" з великих обсягів raw даних.
Ці таблиці — головний бізнес-актив платформи.

- `hero_aggregated_stats` — winrate/pickrate по патчах
- `hero_item_build_stats` — найпопулярніші builds по ролях
- `hero_matchup_stats` — counter/synergy матриця
- `item_effectiveness` — ефективність items по ситуаціях
- Batch job для rebuild цих таблиць (не real-time)

### Phase 5 — Project Health & Refactor 🔜
- Repository refactor (по сутностях)
- Business Logic Audit
- Real API smoke test (перевірка на реальних даних)
- Документація приведена до актуального стану

### Phase 6 — Frontend (React) ⏳
- Окремий сервіс
- Hero stats dashboard
- Item builds
- Meta snapshot

### Phase 7 — Recommendation Engine ⏳
- Rule-based рекомендації
- Counter/synergy picks
- Draft analyzer

### Phase 8 — Public API & Scale ⏳
- Pagination, filters, caching
- PostgreSQL migration
- Docker Compose
- Monitoring

---

## Принципи архітектури

```
External APIs → Raw Ingestion → Normalization
                                      ↓
                            Pre-computed Tables  ← batch jobs (rebuild)
                                      ↓
                            Analytics API  →  Frontend
```

- `db/` не знає про `domains/` і `providers/`
- `domains/` не знає про HTTP і DB
- Pre-computed таблиці будуються batch job'ами, не в real-time
- Аналітика читає з pre-computed — не рахує по raw щоразу
- SQLite (dev) → PostgreSQL (prod)