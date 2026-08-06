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
    pass

    # TODO: Render game screen