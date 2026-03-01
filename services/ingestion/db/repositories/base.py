# services/ingestion/db/repositories/base.py
"""Shared constants для db/repositories/.

Живуть тут щоб не дублювати між файлами.
Кандидати на перенесення в config.py (Epic BL1.6).
"""

# Максимальна довжина error string в ingestion_log
_MAX_ERROR_LEN = 500

# Match phase thresholds (seconds).
# Кандидати на config: MATCH_PHASE_EARLY_MAX_SEC, MATCH_PHASE_MID_MAX_SEC
_EARLY_MAX = 1800   # ≤ 30 хв → 'early'
_MID_MAX = 3000     # 30–50 хв → 'mid'
# > 3000s → 'late'