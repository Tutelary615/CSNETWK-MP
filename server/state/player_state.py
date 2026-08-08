"""
Contains player state data
"""
import random
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

    def shuffle_library(self) -> None:
        random.shuffle(self.library)

    def draw_opening_hand(self, count: int = 7) -> None:
        for _ in range(count):
            self.draw()