# services/ingestion/domains/heroes/meta.py
"""Universal мета героїв по позиціях — НЕ прив'язана до жодного провайдера.

Ключ — офіційна англійська назва героя (localized_name з OpenDota).
hero_id тут НЕМАЄ навмисно — різні провайдери мають різні ID для
одного героя. Маппінг name → id живе в providers/*/hero_id_map.py.

Шкала балів 1–5:
  5 = основна роль, максимально ефективний
  4 = сильна роль, часто грається
  3 = можлива роль (flex)
  2 = рідко, але зустрічається
  1 = майже ніколи

flex_score  = кількість позицій з балом >= 3
primary_pos = позиція з найвищим балом (1=carry..5=hard_support)

Дані актуальні для поточного патча. Підлягають перегляду при
великих змінах балансу. Це статична фікстура — у майбутньому
буде оновлюватись через analytics pipeline.

'Largo' — id=155, новий герой. 'Largo' — робоча назва, англійська
офіційна назва уточнюється при наступному sync_heroes().
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HeroMeta:
    """Мета-оцінка героя по позиціях. Не містить hero_id."""

    pos1: int  # carry
    pos2: int  # mid
    pos3: int  # offlane
    pos4: int  # soft support
    pos5: int  # hard support

    @property
    def scores(self) -> tuple[int, int, int, int, int]:
        return (self.pos1, self.pos2, self.pos3, self.pos4, self.pos5)

    @property
    def flex_score(self) -> int:
        """Кількість позицій з балом >= 3."""
        return sum(1 for s in self.scores if s >= 3)

    @property
    def primary_pos(self) -> int:
        """Позиція з найвищим балом (1-indexed)."""
        return max(range(5), key=lambda i: self.scores[i]) + 1


def _m(p1: int, p2: int, p3: int, p4: int, p5: int) -> HeroMeta:
    """Shorthand для читабельності таблиці."""
    return HeroMeta(pos1=p1, pos2=p2, pos3=p3, pos4=p4, pos5=p5)


# fmt: off
# Universal hero meta: official_name → HeroMeta
# Ключ = localized_name з OpenDota /heroes (англійська назва)
HERO_META: dict[str, HeroMeta] = {
    #                              p1  p2  p3  p4  p5
    "Abaddon":           _m(       4,  3,  4,  3,  4),
    "Alchemist":         _m(       4,  3,  3,  4,  3),
    "Ancient Apparition":_m(       2,  3,  1,  4,  4),
    "Anti-Mage":         _m(       4,  3,  3,  1,  1),
    "Arc Warden":        _m(       3,  4,  3,  2,  1),
    "Axe":               _m(       2,  2,  5,  3,  3),
    "Bane":              _m(       2,  4,  2,  4,  4),
    "Batrider":          _m(       3,  4,  3,  4,  3),
    "Beastmaster":       _m(       3,  4,  4,  2,  2),
    "Bloodseeker":       _m(       4,  3,  3,  2,  1),
    "Bounty Hunter":     _m(       2,  3,  2,  4,  3),
    "Brewmaster":        _m(       2,  4,  5,  3,  2),
    "Bristleback":       _m(       3,  3,  4,  2,  2),
    "Broodmother":       _m(       5,  5,  5,  2,  1),
    "Centaur Warrunner": _m(       2,  2,  4,  1,  1),
    "Chaos Knight":      _m(       3,  2,  4,  3,  2),
    "Chen":              _m(       1,  2,  2,  4,  4),
    "Clinkz":            _m(       5,  3,  2,  2,  1),
    "Clockwerk":         _m(       1,  3,  4,  4,  4),
    "Crystal Maiden":    _m(       1,  1,  3,  4,  5),
    "Dark Seer":         _m(       2,  3,  4,  2,  2),
    "Dark Willow":       _m(       2,  3,  2,  4,  4),
    "Dazzle":            _m(       3,  4,  4,  4,  4),
    "Death Prophet":     _m(       2,  4,  4,  4,  3),
    "Disruptor":         _m(       1,  2,  1,  4,  4),
    "Doom":              _m(       3,  3,  5,  2,  2),
    "Dragon Knight":     _m(       5,  4,  3,  2,  2),
    "Drow Ranger":       _m(       5,  3,  2,  2,  1),
    "Earth Spirit":      _m(       2,  4,  3,  4,  3),
    "Earthshaker":       _m(       2,  4,  3,  4,  3),
    "Elder Titan":       _m(       2,  3,  4,  4,  4),
    "Ember Spirit":      _m(       3,  5,  3,  2,  2),
    "Enchantress":       _m(       1,  3,  2,  4,  4),
    "Enigma":            _m(       2,  3,  4,  4,  3),
    "Faceless Void":     _m(       4,  2,  3,  3,  2),
    "Grimstroke":        _m(       1,  3,  2,  4,  4),
    "Gyrocopter":        _m(       4,  3,  2,  4,  3),
    "Hoodwink":          _m(       2,  3,  2,  5,  4),
    "Huskar":            _m(       5,  5,  4,  3,  3),
    "Invoker":           _m(       2,  4,  2,  3,  2),
    "Io":                _m(       3,  4,  3,  3,  4),
    "Jakiro":            _m(       2,  3,  3,  5,  5),
    "Juggernaut":        _m(       4,  2,  3,  2,  1),
    "Keeper of the Light":_m(      2,  4,  2,  4,  3),
    "Kez":               _m(       4,  4,  2,  2,  2),
    "Kunkka":            _m(       3,  4,  4,  3,  2),
    "Largo":             _m(       2,  2,  4,  4,  4),
    "Legion Commander":  _m(       3,  3,  4,  2,  1),
    "Leshrac":           _m(       2,  5,  2,  4,  3),
    "Lich":              _m(       2,  3,  2,  4,  4),
    "Lifestealer":       _m(       4,  2,  3,  1,  1),
    "Lina":              _m(       4,  5,  2,  4,  3),
    "Lion":              _m(       1,  3,  2,  4,  4),
    "Lone Druid":        _m(       3,  4,  4,  2,  1),
    "Luna":              _m(       4,  3,  2,  3,  2),
    "Lycan":             _m(       4,  3,  4,  1,  1),
    "Magnus":            _m(       3,  4,  4,  4,  3),
    "Marci":             _m(       3,  3,  4,  4,  4),
    "Mars":              _m(       2,  3,  5,  2,  1),
    "Medusa":            _m(       4,  3,  3,  2,  1),
    "Meepo":             _m(       4,  5,  2,  1,  1),
    "Mirana":            _m(       3,  4,  3,  4,  3),
    "Monkey King":       _m(       4,  4,  3,  3,  2),
    "Morphling":         _m(       4,  4,  2,  2,  1),
    "Muerta":            _m(       4,  3,  2,  4,  3),
    "Naga Siren":        _m(       4,  3,  2,  4,  2),
    "Nature's Prophet":  _m(       4,  4,  4,  4,  4),
    "Necrophos":         _m(       2,  4,  4,  2,  2),
    "Night Stalker":     _m(       2,  3,  4,  3,  2),
    "Nyx Assassin":      _m(       1,  3,  2,  4,  2),
    "Ogre Magi":         _m(       2,  4,  4,  4,  4),
    "Omniknight":        _m(       2,  2,  4,  3,  4),
    "Oracle":            _m(       1,  3,  1,  4,  4),
    "Outworld Devourer": _m(       2,  4,  2,  2,  2),
    "Pangolier":         _m(       2,  4,  4,  3,  1),
    "Phantom Assassin":  _m(       4,  3,  2,  2,  1),
    "Phoenix":           _m(       2,  4,  4,  4,  4),
    "Primal Beast":      _m(       2,  4,  4,  3,  2),
    "Puck":              _m(       2,  5,  3,  2,  2),
    "Pudge":             _m(       3,  4,  4,  4,  2),
    "Pugna":             _m(       2,  4,  2,  4,  4),
    "Queen of Pain":     _m(       3,  5,  4,  3,  2),
    "Razor":             _m(       4,  4,  5,  3,  2),
    "Riki":              _m(       3,  4,  2,  3,  1),
    "Ringmaster":        _m(       1,  2,  1,  5,  5),
    "Rubick":            _m(       1,  4,  2,  4,  3),
    "Sand King":         _m(       2,  4,  4,  2,  1),
    "Shadow Demon":      _m(       1,  3,  2,  5,  4),
    "Shadow Fiend":      _m(       5,  4,  2,  2,  1),
    "Shadow Shaman":     _m(       1,  3,  1,  5,  4),
    "Silencer":          _m(       2,  3,  2,  4,  4),
    "Skywrath Mage":     _m(       2,  5,  2,  5,  3),
    "Slardar":           _m(       2,  4,  4,  2,  1),
    "Slark":             _m(       4,  2,  2,  4,  2),
    "Snapfire":          _m(       2,  3,  3,  5,  4),
    "Sniper":            _m(       4,  4,  2,  4,  2),
    "Spectre":           _m(       4,  3,  2,  1,  1),
    "Spirit Breaker":    _m(       1,  3,  3,  4,  3),
    "Storm Spirit":      _m(       2,  4,  1,  2,  1),
    "Sven":              _m(       4,  2,  2,  3,  3),
    "Techies":           _m(       1,  2,  2,  4,  3),
    "Templar Assassin":  _m(       5,  4,  2,  1,  1),
    "Terrorblade":       _m(       5,  2,  4,  3,  2),
    "Tidehunter":        _m(       3,  2,  5,  2,  1),
    "Timbersaw":         _m(       1,  4,  5,  3,  2),
    "Tinker":            _m(       3,  4,  2,  3,  4),
    "Tiny":              _m(       3,  4,  3,  4,  3),
    "Treant Protector":  _m(       2,  2,  3,  4,  4),
    "Troll Warlord":     _m(       4,  2,  2,  1,  1),
    "Tusk":              _m(       1,  3,  2,  4,  4),
    "Underlord":         _m(       2,  2,  4,  2,  2),
    "Undying":           _m(       2,  2,  4,  4,  4),
    "Ursa":              _m(       5,  2,  2,  2,  1),
    "Vengeful Spirit":   _m(       3,  3,  4,  4,  4),
    "Venomancer":        _m(       3,  3,  4,  4,  4),
    "Viper":             _m(       3,  4,  4,  2,  2),
    "Visage":            _m(       3,  4,  4,  3,  3),
    "Void Spirit":       _m(       2,  5,  3,  4,  2),
    "Warlock":           _m(       1,  3,  2,  3,  5),
    "Weaver":            _m(       4,  3,  3,  4,  3),
    "Windranger":        _m(       5,  4,  4,  4,  4),
    "Winter Wyvern":     _m(       2,  3,  4,  4,  4),
    "Witch Doctor":      _m(       1,  2,  1,  4,  4),
    "Wraith King":       _m(       4,  2,  4,  3,  2),
    "Zeus":              _m(       2,  4,  2,  4,  3),
}
# fmt: on
