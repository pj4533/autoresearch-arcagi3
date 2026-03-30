"""Command implementations for the ARC CLI."""
import json
import os
import sys
from pathlib import Path
from typing import Optional

from arcagi3.cli.backends.base import ACTION_MAP, GameBackend
from arcagi3.cli.frame_renderer import render_frame_text, save_frame_image
from arcagi3.cli.session import Session, SESSION_DIR

REPLAY_DIR = Path("experiments/replays")
REPLAY_FRAMES_DIR = REPLAY_DIR / "frames"


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

    # Auto-save initial frame for replay
    _save_replay_frame(session, frame, is_initial=True)


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

    # Auto-save replay frame
    _save_replay_frame(session, frame)


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

    # Auto-generate replay JSONL
    _finalize_replay(session)

    # Auto-append to experiment log
    _auto_log_experiment(session)

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


def _auto_log_experiment(session: Session):
    """Auto-append a row to experiments/log.md."""
    try:
        log_path = Path("experiments/log.md")
        if not log_path.exists():
            return

        # Determine next experiment number
        text = log_path.read_text()
        lines = text.strip().split("\n")
        exp_num = 1
        for line in lines:
            if line.startswith("|") and not line.startswith("| Exp") and "---" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if parts:
                    try:
                        exp_num = max(exp_num, int(parts[0]) + 1)
                    except ValueError:
                        pass

        game_base = session.game_id.split("-")[0] if "-" in session.game_id else session.game_id
        status = "scored" if session.current_score > 0 else "attempted"
        state = session.current_state

        row = (
            f"| {exp_num:03d} | {game_base} | "
            f"arc CLI play | {session.current_score} | {session.action_count} | "
            f"— | {status} | {state} |"
        )

        with open(log_path, "a") as f:
            f.write(row + "\n")

        print(f"\nLogged as exp {exp_num:03d} in experiments/log.md")

    except Exception as e:
        print(f"\nWarning: Could not auto-log: {e}", file=sys.stderr)


def _get_replay_session_id(session: Session) -> str:
    """Generate a replay session ID from game_id and card_id."""
    game_base = session.game_id.split("-")[0] if "-" in session.game_id else session.game_id
    card_short = (session.card_id or "local")[:8]
    return f"{game_base}_{card_short}"


def _save_replay_frame(session: Session, frame, is_initial: bool = False):
    """Auto-save a frame PNG to the replay directory."""
    try:
        REPLAY_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
        session_id = _get_replay_session_id(session)
        step = 0 if is_initial else session.action_count
        frame_filename = f"{session_id}_step{step:03d}.png"
        frame_path = REPLAY_FRAMES_DIR / frame_filename
        save_frame_image(frame, str(frame_path))
    except Exception:
        pass  # Don't let replay failures break gameplay


def _finalize_replay(session: Session):
    """Generate replay JSONL from session action history + saved frames."""
    try:
        REPLAY_DIR.mkdir(parents=True, exist_ok=True)
        session_id = _get_replay_session_id(session)
        replay_file = REPLAY_DIR / f"{session_id}.jsonl"

        entries = []

        # Initial frame (step 0)
        frame_filename = f"{session_id}_step000.png"
        frame_path = REPLAY_FRAMES_DIR / frame_filename
        entries.append({
            "step": 0,
            "action": "(initial state)",
            "reasoning": "",
            "score": 0,
            "state": "NOT_FINISHED",
            "frame_path": f"frames/{frame_filename}" if frame_path.exists() else None,
        })

        # Each action
        score_so_far = 0
        for i, action_entry in enumerate(session.action_history, 1):
            action_name = action_entry.get("action_name", "unknown")
            x = action_entry.get("x", 0)
            y = action_entry.get("y", 0)

            if action_name == "click":
                action_desc = f"click --x {x} --y {y}"
            else:
                action_desc = action_name

            frame_filename = f"{session_id}_step{i:03d}.png"
            frame_path = REPLAY_FRAMES_DIR / frame_filename

            entries.append({
                "step": i,
                "action": action_desc,
                "reasoning": "",  # Claude Code's reasoning isn't captured in CLI
                "score": session.current_score if i == len(session.action_history) else score_so_far,
                "state": session.current_state if i == len(session.action_history) else "NOT_FINISHED",
                "frame_path": f"frames/{frame_filename}" if frame_path.exists() else None,
            })

        with open(replay_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        print(f"\nReplay saved: {replay_file} ({len(entries)} frames)")

    except Exception as e:
        print(f"\nWarning: Could not save replay: {e}", file=sys.stderr)
