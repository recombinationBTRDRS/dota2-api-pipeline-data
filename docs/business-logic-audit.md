# Business Logic Audit — R1.3
> Проведено після Epic 4. Основа для Epic BL1 і подальших рішень.
> Статус кожного пункту: 🔴 Проблема | 🟡 Gap / Рішення потрібне | 🟢 OK | ✅ Вирішено

---

## 1. Adapter — що збирається з API

### 1.1 `adapt_match()` — що береться з матчу

| Поле | Статус | Примітка |
|------|--------|---------|
| `match_id` | 🟢 | |
| `duration` | 🟢 | |
| `radiant_win` | 🟢 | |
| `start_time` | 🟢 | |
| `radiant_score` | 🟡 | Береться в contract dict але **не зберігається** в DB (немає колонки) |
| `dire_score` | 🟡 | Те саме |
| `picks_bans` | 🟡 | Береться але **не зберігається** — потрібно для Draft Analyzer (Epic 7) |
| `patch` | 🔴 | **Не береться з API взагалі**. OpenDota повертає `patch` в match JSON. В `matches` таблиці є колонка але вона завжди NULL |
| `region` | 🔴 | Те саме — є в API (`region`), є колонка в DB, але завжди NULL |
| `game_mode` | 🟡 | Не збираємо. Може бути корисним для фільтрів |
| `league_id` | 🟡 | Не збираємо |

### 1.2 `adapt_player()` — що береться з гравця

| Поле | Статус | Примітка |
|------|--------|---------|
| `player_slot` (0-9) | 🟢 | Нормалізовано через slot_index |
| `account_id` | 🟢 | |
| `hero_id` | 🟢 | |
| `kills/deaths/assists` | 🟢 | |
| `gpm/xpm` | 🟢 | |
| `is_radiant` | 🟡 | Береться але **не зберігається** в DB |
| `win` | 🟢 | |
| `items` (0-5) | 🟢 | |
| `lane_role` | 🔴 | **Не збираємо**. OpenDota повертає `lane_role` (1-4) — реальна позиція в матчі |
| `is_roaming` | 🔴 | **Не збираємо**. Важливо для розрізнення pos4 vs pos5 |
| `rank_tier` | 🔴 | **Не збираємо**. Є в player JSON |
| `backpack_0..2` | 🔴 | **Не збираємо** (слоти 6-8) |
| `item_neutral` | 🔴 | **Не збираємо** (нейтральний слот) |
| `net_worth` | 🟡 | Не збираємо. Корисне для аналітики |
| `hero_damage` | 🟡 | Не збираємо |
| `tower_damage` | 🟡 | Не збираємо |
| `hero_healing` | 🟡 | Не збираємо |
| `last_hits` | 🟡 | Не збираємо |

---

## 2. primary_pos — статика vs реальність

### Поточна логіка:
```
HERO_META (статика в коді)
    ↓ sync_role_scores.py
hero_role_scores.primary_pos (pre-computed, незмінний)
    ↓ analytics (Task 4.2)
get_hero_stats_by_role(hero_id, primary_pos)  ← фільтрує по типовій позиції
```

### Проблема:
`primary_pos` — це **статична типова роль** героя, не реальна позиція в матчі.
Тобто Anti-Mage завжди вважається carry (pos1) незалежно від того де він реально грав.

Аналітика "winrate Anti-Mage на carry" насправді означає
"winrate Anti-Mage в усіх матчах де він вважається carry-героєм".

### Що є в API:
OpenDota повертає `lane_role` в player JSON:
- `1` = Safe Lane (carry)
- `2` = Mid
- `3` = Off Lane
- `4` = Jungle / Support (роумінг)

І `is_roaming: bool` — розрізняє pos4 vs pos5.

### Варіанти рішення:

**Варіант A — Залишити як є (статика):**
- ✅ Простіше
- ✅ Не потребує змін в DB
- ❌ Неточно — не відображає реальний матч

**Варіант B — Додати `lane_role` в `match_players`:**
- Зберігати реальну позицію з кожного матчу
- Analytics рахує по реальній позиції
- ✅ Точні дані
- ⚠️ Потребує: нову колонку `lane_role` в `match_players`, зміну adapter, зміну analytics queries
- ⚠️ `lane_role=4` не розрізняє soft/hard support — потрібен `is_roaming`

**Варіант C — Hybrid:**
- Зберігати `lane_role` + `is_roaming` в `match_players`
- `hero_role_scores` залишити для fallback якщо `lane_role` NULL
- ✅ Найточніший підхід
- ⚠️ Найбільше змін

**🔴 Рекомендація: Варіант B або C — вирішити перед Pre-computed Layer (Epic 5)**
Бо pre-computed таблиці будуть будуватись по `lane_role` — якщо його немає, якість даних низька.

---

## 3. HERO_META — стан і ризики

### Поточний стан:
- 125 героїв вшито в `domains/heroes/meta.py`
- Оновлюється вручну при виході нового героя
- `Largo` (id=155) є — але примітка що "робоча назва"
- `Kez` є — новий герой доданий

### Ризики:
- При виході нового героя треба вручну додати в 2 файли: `meta.py` і `hero_id_map.py`
- При зміні офіційної назви героя (буває) — ключ в `HERO_META` стає невалідним
- `sync_role_scores.py` тихо пропускає (`skipped_no_id`) — важко помітити що щось не так

### Шкала балів (1-5) — суб'єктивна:
Бали виставлені вручну і не оновлюються автоматично при патчах.
Наприклад `Anti-Mage: pos2=3` (flex mid) — в поточному метагеймі це дискусійно.

**🟡 Рішення (BL1.3):** Додати validation при sync — якщо новий герой з'явився в API але не в `HERO_META`, логувати ERROR (не WARNING) щоб не пропустити.

---

## 4. flex_score — як рахується

```python
@property
def flex_score(self) -> int:
    return sum(1 for s in self.scores if s >= 3)
```

Поріг `>= 3` захардкоджений в `HeroMeta.flex_score` property.

Приклади:
- `Nature's Prophet` (5,4,4,4,4) → flex_score=5 — грається скрізь ✅
- `Windranger` (5,4,4,4,4) → flex_score=5 ✅
- `Crystal Maiden` (1,1,3,4,5) → flex_score=3 — pos3=3, але CM офлейн дуже рідко 🟡

**🟡 Рішення (BL1.6):** Поріг `3` перенести в config як `FLEX_SCORE_MIN_THRESHOLD`.

---

## 5. Analytics формули — перегляд

### 5.1 meta_score
```python
meta_score = winrate * pickrate * 100
```
Де `pickrate = matches_played / total_matches_in_sample`.

**Проблема:** якщо вибірка мала (наприклад 50 матчів), meta_score буде нерепрезентативним.
Немає мінімального фільтру — герой з 1 матчем і 1 wins матиме meta_score = 2.0.

**🟡 Рішення:** Додати `min_matches` параметр в `get_meta_snapshot()` (аналогічно `get_role_leaderboard`).

### 5.2 Phase thresholds
```python
_EARLY_MAX = 1800  # 30 хв
_MID_MAX = 3000    # 50 хв
```

Середня тривалість матчу в Dota 2 на high MMR ≈ 35-40 хвилин.
- Більшість матчів потрапляють в "mid" зону (1800-3000s)
- "early" (< 30 хв) = смурф-ігри або forfeit
- "late" (> 50 хв) = рідкість на high MMR

**🟡 Це відображає реальність але є кандидатом на config (BL1.6).**

### 5.3 win_pickrate
```python
win_pickrate = win_times / total_wins
```
Чисельник = скільки разів item був у виграних матчах.
Знаменник = total wins героя.

Це **conditional probability**: P(item | win).
Не те саме що "item збільшує шанс виграшу" — але корисна метрика для item build guide.

**🟢 Формула правильна для поточної задачі.**

---

## 6. sync_role_scores — логіка і edge cases

### Що робить:
1. Читає всі heroes з DB
2. Для кожного імені в HERO_META шукає ID в OPENDOTA_HERO_IDS
3. Якщо hero є в heroes table — зберігає HeroRoleScoreDB

### Edge cases:

**Якщо sync_heroes не запускався:**
- `existing_ids` = порожній set
- Всі герої потрапляють в `skipped_no_hero`
- `sync_role_scores` повертає 0 записів
- ✅ Безпечно — FK constraint не порушується

**Якщо новий герой в API але не в HERO_META:**
- `sync_heroes` збереже нового героя
- `sync_role_scores` пропустить (`skipped_no_id`)
- Hero буде в `heroes` але без `hero_role_scores` запису
- В аналітиці (INNER JOIN) цей герой буде **відсутній**
- 🔴 Тихий збій — analytics не покаже нового героя

**Порядок запуску:**
```
sync_heroes() → sync_role_scores() → ingest_match() → analytics
```
Якщо порядок порушено — heroes table може бути пустою.

**🟡 Рекомендація:** Додати explicit check/error якщо `sync_role_scores` викликається до `sync_heroes`.

---

## 7. Константи — що переносити в config

| Константа | Де зараз | Пропозиція |
|-----------|----------|-----------|
| `_EARLY_MAX = 1800` | `repositories/base.py` | `MATCH_PHASE_EARLY_MAX_SEC` в config |
| `_MID_MAX = 3000` | `repositories/base.py` | `MATCH_PHASE_MID_MAX_SEC` в config |
| `_MAX_ERROR_LEN = 500` | `repositories/base.py` | `INGESTION_LOG_MAX_ERROR_LEN` в config |
| `flex_score >= 3` | `HeroMeta.flex_score` property | `FLEX_SCORE_MIN_THRESHOLD` в config |
| `range(6)` items | `adapters.py` | `DOTA_ITEM_SLOTS = 6` в config або constants |
| `min_matches=10` defaults | різні repos | залишити як default параметри, OK |

---

## 8. Що реально перевірялось на реальних даних

❌ **Нічого.** Всі тести використовують:
- Mock HTTP responses
- Fixtures (JSON файли)
- Seed helpers в tmp SQLite

Реальна поведінка OpenDota API не перевірялась після Epic 1.

**Відомі ризики для R1.4 smoke test:**
- `player.get("account_id")` — анонімні гравці мають `account_id=4294967295` (max uint32), не `None`
- `player["gpm"]` — може бути відсутнім в деяких типах матчів
- `player["win"]` — OpenDota іноді повертає `0/1` замість `bool`
- `radiant_score`/`dire_score` — можуть бути `None` в деяких матчах

---

## 9. Зведена таблиця пріоритетів

| # | Пункт | Пріоритет | Epic |
|---|-------|-----------|------|
| 1 | Додати `lane_role` + `is_roaming` в `match_players` | 🔴 Високий | BL1.2 |
| 2 | Додати `patch` і `region` в `adapt_match()` | 🔴 Високий | BL1.1 |
| 3 | Smoke test на реальних даних | 🔴 Високий | R1.4 |
| 4 | `account_id=4294967295` — анонімний гравець | 🔴 Високий | R1.4 |
| 5 | Backpack items (slots 6-8) і neutral | 🟡 Середній | BL1.3 |
| 6 | Новий герой без HERO_META → ERROR лог | 🟡 Середній | BL1.3 |
| 7 | `meta_score` без min_matches фільтру | 🟡 Середній | BL1.4 |
| 8 | Константи → config | 🟡 Середній | BL1.6 |
| 9 | `radiant_score`/`dire_score` не зберігаються | 🟢 Низький | BL1.1 |
| 10 | `picks_bans` не зберігаються | 🟢 Низький | Draft Analyzer (Epic 7) |

---

## 10. Рекомендована послідовність виправлень

```
R1.4 Smoke test → виявляємо реальні проблеми
    ↓
BL1.1 patch + region в adapt_match + DB
    ↓
BL1.2 lane_role + is_roaming в adapt_player + match_players
    ↓
BL1.3 backpack items + neutral slot
    ↓
BL1.4 meta_score min_matches filter
    ↓
BL1.6 константи → config
    ↓
Epic 5 Pre-computed Layer (з якісними даними)
```