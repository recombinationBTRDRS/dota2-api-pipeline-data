# services/ingestion/tests/domains/test_hero_meta.py
"""Unit-тести для HERO_META і OPENDOTA_HERO_IDS."""
from collections import Counter

from services.ingestion.domains.heroes.meta import HERO_META, HeroMeta
from services.ingestion.providers.opendota.hero_id_map import OPENDOTA_HERO_IDS

# ── HeroMeta dataclass ────────────────────────────────────────────────────────

def test_hero_meta_flex_score() -> None:
    """flex_score = кількість позицій >= 3."""
    m = HeroMeta(pos1=4, pos2=3, pos3=3, pos4=1, pos5=1)
    assert m.flex_score == 3


def test_hero_meta_primary_pos() -> None:
    """primary_pos = позиція з найвищим балом."""
    m = HeroMeta(pos1=4, pos2=3, pos3=3, pos4=1, pos5=1)
    assert m.primary_pos == 1

    m2 = HeroMeta(pos1=1, pos2=2, pos3=1, pos4=5, pos5=5)
    assert m2.primary_pos == 4  # перша з max


def test_hero_meta_scores_tuple() -> None:
    m = HeroMeta(pos1=4, pos2=3, pos3=3, pos4=1, pos5=1)
    assert m.scores == (4, 3, 3, 1, 1)


# ── HERO_META ─────────────────────────────────────────────────────────────────

def test_hero_meta_no_hero_ids() -> None:
    """HERO_META не містить жодних int hero_id."""
    for name, meta in HERO_META.items():
        assert isinstance(name, str), f"Key must be str, got {type(name)}"
        assert isinstance(meta, HeroMeta), f"Value must be HeroMeta for {name}"
        # HeroMeta не має атрибуту hero_id
        assert not hasattr(meta, "hero_id"), f"{name}: HeroMeta must not have hero_id"


def test_hero_meta_size() -> None:
    """HERO_META має не менше 120 героїв."""
    assert len(HERO_META) >= 120


def test_hero_meta_scores_valid_range() -> None:
    """Всі бали в діапазоні 1–5."""
    for name, meta in HERO_META.items():
        for i, score in enumerate(meta.scores, 1):
            assert 1 <= score <= 5, f"{name} pos{i}={score} out of range 1-5"


def test_hero_meta_known_heroes() -> None:
    """Перевіряємо конкретні відомі значення."""
    am = HERO_META["Anti-Mage"]
    assert am.pos1 == 4
    assert am.flex_score == 3
    assert am.primary_pos == 1

    cm = HERO_META["Crystal Maiden"]
    assert cm.pos5 == 5
    assert cm.primary_pos == 5

    np = HERO_META["Nature's Prophet"]
    assert np.flex_score == 5  # 4,4,4,4,4 → всі >= 3

    windranger = HERO_META["Windranger"]
    assert windranger.flex_score == 5  # 5,4,4,4,4


def test_hero_meta_largo_present() -> None:
    """Largo (id=155) є в HERO_META."""
    assert "Largo" in HERO_META
    largo = HERO_META["Largo"]
    assert largo.scores == (2, 2, 4, 4, 4)
    assert largo.flex_score == 3


# ── OPENDOTA_HERO_IDS ─────────────────────────────────────────────────────────

def test_opendota_ids_no_duplicates() -> None:
    """Всі hero_id унікальні."""
    counts = Counter(OPENDOTA_HERO_IDS.values())
    dupes = {name: hid for name, hid in OPENDOTA_HERO_IDS.items()
             if counts[hid] > 1}
    assert not dupes, f"Duplicate IDs: {dupes}"


def test_opendota_ids_known_values() -> None:
    """Верифіковані ID."""
    assert OPENDOTA_HERO_IDS["Anti-Mage"] == 1
    assert OPENDOTA_HERO_IDS["Axe"] == 2
    assert OPENDOTA_HERO_IDS["Ringmaster"] == 131
    assert OPENDOTA_HERO_IDS["Marci"] == 136
    assert OPENDOTA_HERO_IDS["Kez"] == 145
    assert OPENDOTA_HERO_IDS["Largo"] == 155
    assert OPENDOTA_HERO_IDS["Lone Druid"] == 80
    assert OPENDOTA_HERO_IDS["Treant Protector"] == 83
    assert OPENDOTA_HERO_IDS["Nature's Prophet"] == 53
    assert OPENDOTA_HERO_IDS["Outworld Devourer"] == 76


def test_meta_and_id_map_coverage() -> None:
    """Кожен герой з HERO_META є в OPENDOTA_HERO_IDS і навпаки."""
    meta_names = set(HERO_META.keys())
    id_names = set(OPENDOTA_HERO_IDS.keys())

    only_in_meta = meta_names - id_names
    only_in_ids = id_names - meta_names

    assert not only_in_meta, f"In HERO_META but missing from OPENDOTA_HERO_IDS: {only_in_meta}"
    assert not only_in_ids, f"In OPENDOTA_HERO_IDS but missing from HERO_META: {only_in_ids}"
