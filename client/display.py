"""
Display screen for the visible game state of client/player
"""
import os

def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")

def render_lobby(state: dict, my_id: str) -> None:
    print("\n" + "=" * 50)
    print(" LOBBY ")
    print("=" * 50)
    print(f"Player: {my_id}")
    print(f"Players ready: {state.get('players_ready', 0)} / 2")
    waiting = state.get("waiting_for", [])
    if waiting:
        print(f"Waiting for:  {', '.join(waiting)}")
    else:
        print(" Both players ready! Starting soon...")
    print("=" * 50)

def render_game(state: dict, my_id: str) -> None:
    clear_screen()

    turn = state.get("turn", "?")
    phase = state.get("phase", "?")
    ap = state.get("active_player", "?")
    lifes = state.get("life_totals", {})
    bf = state.get("battlefield", {})
    gy = state.get("graveyard", {})
    hand = state.get("hand", {}).get(my_id, [])
    hcounts = state.get("hand_counts", {})
    libs = state.get("library_counts", {})

    print("\n" + "=" * 60)
    print(f" Turn {turn} | Phase: {phase} | Active: {ap}")
    print("=" * 60)

    for pid, life, in lifes.items():
        marker = " <- YOU" if pid == my_id else ""
        print(f" {pid}: {life} life{marker}")

    print()

    for pid in lifes:
        if pid != my_id:
            opp_hand = hcounts.get(pid, "?")
            opp_lib = libs.get(pid, "?")
            opp_bf = bf.get(pid, [])
            opp_gy = gy.get(pid, [])
            print(f" [{pid}]")
            print(f" Library: {opp_lib} cards      Hand: {opp_hand} cards")
            print(" Battlefield: pending")
            print(f" Graveyard: { opp_gy or '(empty)'}")

    