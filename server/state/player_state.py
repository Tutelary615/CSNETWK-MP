"""
Contains player state data
"""
import random
from typing import Optional
from shared.constants import STARTING_LIFE
from dataclasses import dataclass, field

@dataclass
class PlayerState:
    player_id: str
    life: int = STARTING_LIFE
    library: list[str] = field(default_factory=list)
    hand: list[str] = field(default_factory=list)
    graveyard: list[str] = field(default_factory=list)
    battlefield: list[str] = field(default_factory=list)

    # For mulligan
    mulligan_count: int = 0
    has_kept: bool = False 

    def shuffle_library(self) -> None:
        random.shuffle(self.library)

    # Draw the top card and return card_id
    def draw(self) -> Optional[str]:
        if not self.library:
            return None
        card_id = self.library.pop(0)
        self.hand.append(card_id)

    def draw_opening_hand(self, count: int = 7) -> None:
        for _ in range(count):
            self.draw()