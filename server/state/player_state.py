"""
Contains player state data
"""
from shared.constants import STARTING_LIFE
from dataclasses import dataclass, field

@dataclass
class PlayerState:
    player_id: str
    life = STARTING_LIFE