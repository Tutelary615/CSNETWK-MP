"""
Card dataclass and loads the card set; this should be called at startup
"""

import json
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class Card:
    id: str
    name: str
    card_type: str

    mana_cost: dict
    colors: list[str]

    # For creature-only fields
    power: Optional[int] = None
    toughness: Optional[int] = None

    effect: Optional[dict] = None

    # Keyword abilities
    keywords: list[str] = field(default_factory=list)

    @property
    def is_land(self) -> bool:
        return self.card_type == "land"

    @property
    def is_creature(self) -> bool:
        return self.card_type == "creature"

    @property
    def is_instant(self) -> bool:
        return self.card_type == "instant"

    @property
    def is_sorcery(self) -> bool:
        return self.card_type == "sorcery"

    @property
    def has_haste(self) -> bool:
        return "haste" in self.keywords

    @property
    def has_first_strike(self) -> bool:
        return "first_strike" in self.keywords

    @property
    def has_double_strike(self) -> bool:
        return "double_strike" in self.keywords

_catalog: dict[str, Card] = {}

def load_catalog(path: str | Path) -> dict[str, Card]:
    global _catalog
    if _catalog:
        return _catalog

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    for entry in raw:
        card = Card(
            id        = entry["id"],
            name      = entry["name"],
            card_type = entry["card_type"],
            mana_cost = entry.get("mana_cost", {}),
            colors    = entry.get("colors", []),
            power     = entry.get("power"),
            toughness = entry.get("toughness"),
            effect    = entry.get("effect"),
            keywords  = entry.get("keywords", []),
        )

        _catalog[card.id] = card

    return _catalog

def is_valid_card_id(card_id: str) -> bool:
    return card_id in _catalog

    