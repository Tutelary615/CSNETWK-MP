"""
Display screen for the visible game state of client/player
"""
import os

def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")

def render_lobby(state: dict, my_id: str, my_name: str) -> None:
    print("\n" + "=" * 50)
    print(" LOBBY ")
    print("=" * 50)
    print(f"Player: {my_name} (id: {my_id})")
    print(f"Players ready: {state.get('players_ready', 0)} / 2")
    waiting = state.get("waiting_for", [])
    if waiting:
        print(f"Waiting for: {', '.join(waiting)}")
    else:
        print("Both players ready! Starting soon...")
    print("=" * 50)

def render_game(state: dict, my_id: str, my_name: str) -> None:
    clear_screen()

    turn = state.get("turn", "?")
    ap = state.get("active_player", "?")
    phase = state.get("phase", "?")
    holder = state.get("priority_holder")
    lifes = state.get("life_totals", {})
    stack = state.get("stack", [])
    bf = state.get("battlefield", {})
    gy = state.get("graveyard", {})
    hand = state.get("hand", {}).get(my_id, [])
    hcounts = state.get("hand_counts", {})
    libs = state.get("library_counts", {})
    land = state.get("land_played_this_turn", False)

    print("\n" + "=" * 60)
    print(f" Turn {turn} | Phase: {phase} | Active: {ap}")
    print("=" * 60)

    for pid, life, in lifes.items():
        marker = " <- YOU" if pid == my_id else ""
        print(f" {my_name}: {life} life{marker}")

    print()

    for pid in lifes:
        if pid != my_id:
            opp_hand = hcounts.get(pid, "?")
            opp_lib = libs.get(pid, "?")
            opp_bf = bf.get(pid, [])
            opp_gy = gy.get(pid, [])
            print(f" [{pid}]")
            print(f" Library: {opp_lib} cards      Hand: {opp_hand} cards")
            print(f" Battlefield: {_format_battlefield(my_bf)}")
            print(f" Graveyard: { opp_gy or '(empty)'}")


    print()
    print(" --- THE STACK ---")
    # TODO: Print stack display here

    print()
    print(" --- YOUR BOARD --- ")
    my_bf = bf.get(my_id, [])
    my_gy = gy. get(my_id, [])
    my_lib = libs.get(my_id, "?")
    print(f" Library: {my_lib} cards")
    print(f" Battlefield: {_format_battlefield(my_bf)}")
    print(f" Graveyard: {my_gy or '(empty)'}")

    print()
    print(" --- YOUR HAND ---")
    if hand:
        for i, card_id in enumerate(hand):
            print(f" [{i}] {card_id}")
    else:
        print(" (empty)")

    print()

    if holder:
        if holder == my_id:
            print("Priority: YOU")
        else:
            print(f"Priority: {holder} (waiting...)")
    print("=" * 60)
    print()

    print("Your move: ")

def render_game_over(pdu: dict, my_id: str) -> None:
    print("\n" + "=" * 50)
    print("GAME OVER")
    print("=" * 50)
    winner = pdu.get("winner_id", "?")
    reason = pdu.get("reason", "?")
    if winner == my_id:
        print("YOU WIN!")
    else:
        print("YOU LOSE.")
    print(f"Reason: {reason}")
    print("=" * 50)
    print()

def render_error(pdu: dict) -> None:
    print(f"\n [ERROR] {pdu.get('code')}: {pdu.get('message')}")

def _format_battlefield(perms: list) -> str:
    if not perms:
        return "(empty)"

    