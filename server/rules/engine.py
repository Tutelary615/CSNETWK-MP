"""
Applies card effects to the game state

TODO: Expand per card effect
"""
import logging
from server.state.permanent import Permanent

logger = logging.getLogger(__name__)


class RulesEngine:
    def __init__(self, game_server):
        self.gs = game_server
        self.state = game_server.state
        self.card_catalog = game_server.card_catalog

    async def apply_effect(self, item) -> list[dict]:
        #Apply the effect of a resolved StackItem.

        card = self.card_catalog.get(item.source_id)
        if card is None or card.effect is None:
            return []

        state_changes = []
        effect = card.effect

        # Direct damage
        if "damage" in effect:
            amount = effect["damage"]["amount"]
            for target_id in item.targets:
                self._apply_damage(target_id, amount)
                state_changes.append({
                    "change_type": "DAMAGE",
                    "target": target_id,
                    "amount": amount,
                })

        # Creature entering battlefield
        if card.is_creature and item.item_type == "SPELL":
            controller = self.state.get_player(item.controller_id)
            if controller:
                perm = Permanent(
                    card_id = item.source_id,
                    owner_id = item.controller_id,
                    controller_id = item.controller_id,
                    tapped = False,
                    summoning_sick = True,
                    power = card.power,
                    toughness = card.toughness,
                    keywords = list(card.keywords),
                )
                controller.battlefield.append(perm)
                state_changes.append({
                    "change_type": "ENTERS_BATTLEFIELD",
                    "target": item.source_id,
                    "controller": item.controller_id,
                })
                logger.info("'%s' entered battlefield under '%s'.",
                            item.source_id, item.controller_id)

            # Move card to graveyard after resolution (creatures go to GY from stack)
            # (In real MTG, the creature goes to BF not GY when it resolves,
            #  but non-creature spells go to GY. We handle creature resolution above.)

        elif not card.is_creature:
            # Non-creature spells go to graveyard after resolving
            owner = self.state.get_player(item.controller_id)
            if owner and item.source_id not in [p.card_id for p in owner.battlefield]:
                owner.graveyard.append(item.source_id)

        return state_changes

    # Internal helpers
    def _apply_damage(self, target_id: str, amount: int) -> None:
        # Apply damage to creature
        if target_id in self.state.player_ids:
            player = self.state.get_player(target_id)
            if player:
                player.life -= amount
                logger.info("Dealt %d damage to player '%s' (life now %d).",
                            amount, target_id, player.life)
        else:
            # Find the permanent on any battlefield
            for player in self.state.players.values():
                perm = player.get_permanent(target_id)
                if perm:
                    perm.damage += amount
                    logger.info("Dealt %d damage to creature '%s'.", amount, target_id)
                    break