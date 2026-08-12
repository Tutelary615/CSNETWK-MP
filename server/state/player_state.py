"""
Contains player state data
"""
import random
from typing import Optional
from shared.constants import STARTING_LIFE
from server.state.permanent import Permanent
from dataclasses import dataclass, field

@dataclass
class PlayerState:
    player_id: str

    life: int = STARTING_LIFE
    library: list[str] = field(default_factory=list)
    hand: list[str] = field(default_factory=list)
    graveyard: list[str] = field(default_factory=list)
    battlefield: list[Permanent] = field(default_factory=list)
    land_played_this_turn: bool = False

    # For mulligan
    mulligan_count: int = 0
    has_kept: bool = False 

    # Mana is computed atomically
    mana_pool: dict[str, int] = field(default_factory=dict)

    pending_mulligan_seq: Optional[int] = None

    def shuffle_library(self) -> None:
        random.shuffle(self.library)

    # Draw the top card and return card_id
    def draw(self) -> Optional[str]:
        if not self.library:
            return None
        card_id = self.library.pop(0)
        self.hand.append(card_id)
        return card_id

    def draw_opening_hand(self, count: int = 7) -> None:
        for _ in range(count):
            self.draw()

    # Battlefield helpers
    def untap_all(self) -> None:
        for perm in self.battlefield:
            perm.tapped = False
            perm.summoning_sick = False # cleared on untap (start of your turn)

    def get_permanent(self, card_id: str) -> Optional[Permanent]:
        for p in self.battlefield:
            if p.card_id == card_id:
                return p
        return None

    def remove_permanent(self, card_id: str) -> Optional[Permanent]:
        for i, p in enumerate(self.battlefield):
            if p.card_id == card_id:
                return self.battlefield.pop(i)
        return None

    # Mana helpers
    def available_mana(self, card_catalog: dict) -> dict[str, int]:
        # Return a dict of available mana from untapped lands and mana creatures.
        
        pool: dict[str, int] = {}
        for perm in self.battlefield:
            if perm.tapped:
                continue
            card = card_catalog.get(perm.card_id)
            if not card or not card.effect:
                continue
            produces = card.effect.get("produces", {})
            for color, amount in produces.items():
                pool[color] = pool.get(color, 0) + amount
        return pool

    def can_pay(self, mana_cost: dict, card_catalog: dict) -> bool:
        # Check if player can pay mana cost
        # TODO: implement generic mana matching across color sources.
        
        available = self.available_mana(card_catalog)
        for color, amount in mana_cost.items():
            if color == "generic":
                total_available = sum(available.values())
                if total_available < amount:
                    return False
            else:
                if available.get(color, 0) < amount:
                    return False
        return True

    def tap_for_mana_cost(self, mana_cost: dict, card_catalog: dict) -> bool:
        # Build list of (permanent, color_produced) for untapped mana sources
        sources = []
        for perm in self.battlefield:
            if perm.tapped:
                continue
            card = card_catalog.get(perm.card_id)
            if not card or not card.effect:
                continue
            produces = card.effect.get("produces", {})
            for color, amount in produces.items():
                for _ in range(amount):
                    sources.append((perm, color))

        chosen: list = []
        remaining_colored = dict(mana_cost)
        generic_needed = remaining_colored.pop("generic", 0)

        # Pay colored costs first
        for color, amount in list(remaining_colored.items()):
            need = amount
            for perm, produced_color in sources:
                if need <= 0:
                    break
                if produced_color == color and perm not in [c for c, _ in chosen]:
                    chosen.append((perm, produced_color))
                    need -= 1
            if need > 0:
                return False  # not enough of that color

        # Pay generic from whatever's left over
        used_perms = {perm for perm, _ in chosen}
        leftover = [s for s in sources if s[0] not in used_perms]
        if len(leftover) < generic_needed:
            return False

        for perm, color in leftover[:generic_needed]:
            chosen.append((perm, color))

        # All selections valid -- now actually tap them
        for perm, _ in chosen:
            perm.tapped = True
        return True