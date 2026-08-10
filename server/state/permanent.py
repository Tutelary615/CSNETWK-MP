"""
Holds the Permanent card instance on the battlefield
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Permanent:
    card_id: str
    owner_id: str
    controller_id: str
    tapped: bool
    damage: int = 0
    summoning_sick: bool = True

    power: Optional[int] = None
    toughness: Optional[int] = None
    keywords: list = field(default_factory=list)

    @property
    def has_haste(self) -> bool:
        return "haste" in self.keywords

    @property
    def effective_summoning_sick(self) -> bool:
        return self.summoning_sick and not self.has_haste