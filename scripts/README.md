# Scripts — Документація

Утиліти для ручного керування pipeline: інгест матчів, discovery, дебаг БД.

> Всі скрипти запускаються з кореня проекту з активованим venv.

---

## batch_ingest.py

Інгестує матчі з CSV файлу або списку match_id.

```bash
# З CSV файлу (один match_id на рядок або колонка match_id)
python scripts/batch_ingest.py --csv matches.csv

# Прямо через аргументи
python scripts/batch_ingest.py --ids 8709253716 8710000000 8711000000

# Dry-run — показати що буде без реального запиту
python scripts/batch_ingest.py --csv matches.csv --dry-run

# Rebuild pre-computed після інгесту
python scripts/batch_ingest.py --csv matches.csv --rebuild

# Перезаписати вже відомі матчі (за замовчуванням пропускаються)
python scripts/batch_ingest.py --csv matches.csv --no-skip-known

# Змінити затримку між запитами (default: 1.5 сек)
python scripts/batch_ingest.py --csv matches.csv --rate-limit 2.0
```

**Формат CSV:**
```
match_id          ← з заголовком
8709253716
8714895325
```
або без заголовка — один match_id на рядок.

**Аргументи:**

| Аргумент | Default | Опис |
|----------|---------|------|
| `--csv PATH` | — | CSV файл з match_id |
| `--ids N N...` | — | Список match_id через пробіл |
| `--skip-known` | True | Пропускати вже відомі матчі |
| `--no-skip-known` | — | Перезаписувати вже відомі |
| `--dry-run` | False | Тільки показати план без запитів |
| `--rebuild` | False | Rebuild pre-computed після інгесту |
| `--rate-limit FLOAT` | 1.5 | Секунд між запитами |

---

## discover_and_ingest.py

Discovery матчів через OpenDota Explorer + інгест з фільтрами.

```bash
# Знайти 200 матчів Divine+ і інгестувати
python scripts/discover_and_ingest.py --count 200 --rank-tier 70

# Dry-run — перевірити скільки знайде без інгесту
python scripts/discover_and_ingest.py --count 100 --rank-tier 60 --dry-run

# Тільки discovery — зберегти match_id в CSV
python scripts/discover_and_ingest.py --count 500 --save-csv found.csv --no-ingest

# Повний pipeline: знайти → інгестувати → rebuild
python scripts/discover_and_ingest.py --count 100 --rank-tier 70 --rebuild
```

**Аргументи:**

| Аргумент | Default | Опис |
|----------|---------|------|
| `--count N` | 100 | Кількість матчів |
| `--rank-tier N` | 60 | Мін. rank tier: 60=Ancient+, 70=Divine+, 80=Immortal+ |
| `--lobby-type N` | 7 | Тип лобі: 7=ranked |
| `--dry-run` | False | Показати план без запитів |
| `--no-ingest` | False | Тільки discovery, без інгесту |
| `--save-csv PATH` | — | Зберегти знайдені match_id в CSV |
| `--rebuild` | False | Rebuild pre-computed після інгесту |
| `--rate-limit FLOAT` | 1.5 | Секунд між запитами |
| `--skip-known` | True | Пропускати відомі матчі |

> **Обмеження OpenDota Explorer (2026-03):**
> Колонки `patch` і `region` відсутні в `public_matches`.
> Фільтрація можлива тільки по `lobby_type` і `avg_rank_tier`.

---

## smoke_test.py

Повний smoke test pipeline на 1 реальному матчі.

```bash
python scripts/smoke_test.py
```

Перевіряє: sync heroes → sync items → ingest → analytics.

---

## check_matches.py / check_table.py

Діагностичні скрипти для перевірки стану БД.

```bash
python scripts/check_matches.py   # player_slot розподіл по матчах
python scripts/check_table.py     # DDL таблиці hero_synergy_computed
```

---

## Типовий workflow для збору даних

```bash
# 1. Знайти 500 матчів і зберегти в CSV (швидко, без інгесту)
python scripts/discover_and_ingest.py --count 500 --save-csv found.csv --no-ingest

# 2. Перевірити CSV
head found.csv

# 3. Інгестувати порціями (можна переривати і продовжувати — skip-known)
python scripts/batch_ingest.py --csv found.csv

# 4. Rebuild аналітики
python scripts/batch_ingest.py --csv found.csv --rebuild
# або якщо вже всі заінгестовані:
curl -X POST http://localhost:8000/computed/rebuild
```

---

## Нотатки по OpenDota API

- Free tier: 60 req/min — `--rate-limit 1.5` це безпечно
- Explorer max: 1000 рядків за запит
- Матчі доступні одразу після завершення, але `lane_role` заповнюється
  тільки якщо матч парсений OpenDota (не всі матчі парсяться)