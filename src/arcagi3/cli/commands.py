"""Command implementations for the ARC CLI."""
import sys
from typing import Optional

from arcagi3.cli.backends.base import ACTION_MAP, GameBackend
from arcagi3.cli.frame_renderer import render_frame_text, save_frame_image
from arcagi3.cli.session import Session, SESSION_DIR


def _create_backend(backend_mode: str) -> GameBackend:
    """Create the appropriate backend."""
    if backend_mode == "api":
        from arcagi3.cli.backends.api_backend import APIBackend
        return APIBackend()
    else:
        from arcagi3.cli.backends.local_backend import LocalBackend
        return LocalBackend()


def _restore_backend(session: Session) -> GameBackend:
    """Create a backend and restore its state from session."""
    backend = _create_backend(session.backend)

    if session.backend == "api":
        backend.card_id = session.card_id
        backend.game_id = session.game_id
        backend.guid = session.guid
    elif session.backend == "local":
        # Replay all past actions to restore local game state
        if session.action_history:
            backend.replay_actions(session.game_id, session.action_history)
        else:
            backend.reset(session.game_id)

    return backend


def cmd_list_games(backend_mode: str):
    """List available games."""
    backend = _create_backend(backend_mode)
    games = backend.list_games()

    if not games:
        print("No games available.")
        return

    print(f"{'Game ID':<30} {'Title':<20}")
    print("-" * 50)
    for g in games:
        game_id = g.get("game_id", "")
        title = g.get("title", "")
        print(f"{game_id:<30} {title:<20}")


def cmd_start(game_id: str, backend_mode: str, max_actions: int):
    """Start a new game session."""
    if Session.exists():
        print("Error: A session is already active.", file=sys.stderr)
        print("End it with: arc end", file=sys.stderr)
        sys.exit(1)

    backend = _create_backend(backend_mode)

    # Open scorecard for API backend
    card_id = None
    if backend_mode == "api":
        card_id = backend.open_scorecard([game_id])

    # Reset game to get initial frame
    frame = backend.reset(game_id)

    # Create session
    session = Session(
        game_id=game_id,
        backend=backend_mode,
        card_id=card_id,
        guid=frame.guid,
        max_actions=max_actions,
        action_count=0,
        current_score=frame.levels_completed,
        current_state=frame.state,
    )
    session.save()

    # Print initial state
    output = render_frame_text(
        frame,
        game_id=game_id,
        action_count=0,
        max_actions=max_actions,
    )
    print(output)


def cmd_action(action_name: str, x: int = 0, y: int = 0, image: bool = False):
    """Execute a game action."""
    session = Session.load()

    if not session.is_active:
        print(f"Error: Game is {session.current_state}. Cannot take actions.", file=sys.stderr)
        sys.exit(1)

    if session.max_actions > 0 and session.actions_remaining <= 0:
        print("Error: No actions remaining.", file=sys.stderr)
        sys.exit(1)

    if action_name not in ACTION_MAP:
        valid = ", ".join(ACTION_MAP.keys())
        print(f"Error: Unknown action '{action_name}'. Valid: {valid}", file=sys.stderr)
        sys.exit(1)

    # Store previous frame for diff
    previous_frame = session.previous_frame

    # Create backend and restore state
    backend = _restore_backend(session)

    # Execute the new action
    frame = backend.action(action_name, x=x, y=y)

    # Record in session
    session.record_action(action_name, frame, x=x, y=y)
    session.save()

    # Render output
    output = render_frame_text(
        frame,
        previous_frame=previous_frame,
        game_id=session.game_id,
        action_count=session.action_count,
        max_actions=session.max_actions,
    )
    print(output)

    # Save image if requested
    if image:
        img_path = f"{SESSION_DIR}/frame.png"
        save_frame_image(frame, img_path)
        print(f"\nFrame saved to {img_path}")


def cmd_state(image: bool = False):
    """View current game state."""
    session = Session.load()

    # Restore backend to get current state
    backend = _restore_backend(session)
    frame = backend.get_state()

    output = render_frame_text(
        frame,
        game_id=session.game_id,
        action_count=session.action_count,
        max_actions=session.max_actions,
    )
    print(output)

    if image:
        img_path = f"{SESSION_DIR}/frame.png"
        save_frame_image(frame, img_path)
        print(f"\nFrame saved to {img_path}")


def cmd_end():
    """End the current session."""
    session = Session.load()

    # Close scorecard for API backend
    if session.backend == "api" and session.card_id:
        try:
            backend = _create_backend("api")
            backend.card_id = session.card_id
            backend.close_scorecard()
        except Exception as e:
            print(f"Warning: Could not close scorecard: {e}", file=sys.stderr)

    # Print summary
    print(f"=== Session Summary: {session.game_id} ===")
    print(f"Backend: {session.backend}")
    print(f"Final State: {session.current_state}")
    print(f"Score: {session.current_score} levels completed")
    print(f"Actions Taken: {session.action_count} / {session.max_actions}")

    if session.action_history:
        print(f"\nAction History:")
        for i, entry in enumerate(session.action_history, 1):
            name = entry["action_name"]
            if name == "click":
                print(f"  {i}. {name} (x={entry.get('x', 0)}, y={entry.get('y', 0)})")
            else:
                print(f"  {i}. {name}")

    # Clean up
    Session.delete()
    print("\nSession ended.")


def cmd_info():
    """Show session info."""
    session = Session.load()

    print(f"Game: {session.game_id}")
    print(f"Backend: {session.backend}")
    print(f"State: {session.current_state}")
    print(f"Score: {session.current_score} levels completed")
    print(f"Actions: {session.action_count} / {session.max_actions}")

    if session.card_id:
        print(f"Card ID: {session.card_id}")
    if session.guid:
        print(f"GUID: {session.guid}")

    remaining = session.actions_remaining
    if remaining >= 0:
        print(f"Remaining: {remaining} actions")
    else:
        print("Remaining: unlimited")
