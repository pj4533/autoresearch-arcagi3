"""Command implementations for the ARC CLI."""
import json
import os
import sys
from pathlib import Path
from typing import Optional

from arcagi3.cli.backends.base import ACTION_MAP, GameBackend
from arcagi3.cli.frame_renderer import render_frame_text, save_frame_image
from arcagi3.cli.session import Session, ScorecardSession, SESSION_DIR

REPLAY_DIR = Path("experiments/replays")
REPLAY_FRAMES_DIR = REPLAY_DIR / "frames"
SCORECARDS_DIR = Path("experiments/scorecards")

ALL_GAME_IDS = [
    "ar25-e3c63847", "bp35-0a0ad940", "cd82-fb555c5d", "cn04-65d47d14",
    "dc22-4c9bff3e", "ft09-0d8bbf25", "g50t-5849a774", "ka59-9f096b4a",
    "lf52-271a04aa", "lp85-305b61c3", "ls20-9607627b", "m0r0-dadda488",
    "r11l-aa269680", "re86-4e57566e", "s5i5-a48e4b1d", "sb26-7fbdac44",
    "sc25-f9b21a2f", "sk48-41055498", "sp80-0ee2d095", "su15-4c352900",
    "tn36-ab4f63cc", "tr87-cd924810", "tu93-2b534c15", "vc33-9851e02b",
    "wa30-ee6fef47",
]


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

    # If a scorecard is active, use its card_id and backend
    card_id = None
    if ScorecardSession.exists():
        sc = ScorecardSession.load()
        card_id = sc.card_id
        backend_mode = sc.backend

    backend = _create_backend(backend_mode)

    # Open per-game scorecard only if NOT in a scorecard session
    if not card_id and backend_mode == "api":
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
    in_scorecard = ScorecardSession.exists()

    # Close per-game scorecard ONLY if NOT in a multi-game scorecard
    if not in_scorecard and session.backend == "api" and session.card_id:
        try:
            backend = _create_backend("api")
            backend.card_id = session.card_id
            backend.close_scorecard()
        except Exception as e:
            print(f"Warning: Could not close scorecard: {e}", file=sys.stderr)

    # Print summary
    print(f"=== Game Summary: {session.game_id} ===")
    print(f"Final State: {session.current_state}")
    print(f"Score: {session.current_score} levels completed")
    print(f"Actions Taken: {session.action_count} / {session.max_actions}")

    # Auto-generate replay JSONL
    _finalize_replay(session)

    if in_scorecard:
        # Record result in scorecard session (don't log to log.md yet)
        sc = ScorecardSession.load()
        sc.record_game(
            session.game_id,
            score=session.current_score,  # levels completed; server computes real score
            actions=session.action_count,
            levels_completed=session.current_score,
            state=session.current_state,
        )
        sc.save()
        print(f"\nRecorded in scorecard ({sc.games_completed}/{sc.games_total} games done)")
        print(f"Use 'arc scorecard next' to advance to the next game.")
    else:
        # Standalone game: log to log.md and regenerate dashboard
        _auto_log_experiment(session)
        _regenerate_dashboard()

    # Clean up game session
    Session.delete()
    print("\nGame ended.")


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


def cmd_scorecard_open(max_actions: int):
    """Open a new scorecard with all 25 games."""
    if ScorecardSession.exists():
        print("Error: A scorecard is already active.", file=sys.stderr)
        print("Check status with: arc scorecard status", file=sys.stderr)
        sys.exit(1)

    # Use API backend for real scorecard tracking via local server
    backend = _create_backend("api")
    card_id = backend.open_scorecard(ALL_GAME_IDS)

    if not card_id:
        print("Error: Failed to open scorecard.", file=sys.stderr)
        sys.exit(1)

    # Determine experiment ID from log
    exp_num = _next_experiment_number()
    exp_id = f"SC{exp_num:03d}"

    sc = ScorecardSession(
        card_id=card_id,
        backend="api",
        game_list=list(ALL_GAME_IDS),
        max_actions_per_game=max_actions,
        experiment_id=exp_id,
    )
    sc.save()

    print(f"=== Scorecard Opened: {exp_id} ===")
    print(f"Card ID: {card_id}")
    print(f"Games: {len(ALL_GAME_IDS)}")
    print(f"Max actions per game: {max_actions}")
    print(f"\nStarting game 1/{len(ALL_GAME_IDS)}: {ALL_GAME_IDS[0]}")

    # Auto-start first game
    cmd_start(ALL_GAME_IDS[0], "api", max_actions)


def cmd_scorecard_next():
    """End current game and start the next one in the scorecard."""
    if not ScorecardSession.exists():
        print("Error: No active scorecard.", file=sys.stderr)
        sys.exit(1)

    # End current game if one is active
    if Session.exists():
        cmd_end()

    sc = ScorecardSession.load()
    sc.advance()
    sc.save()

    if sc.is_complete:
        print(f"\n=== All {sc.games_total} games complete! ===")
        print(f"Running score: {sc.running_score:.2f}")
        print(f"Run 'arc scorecard close' to finalize and get official score.")
        return

    next_game = sc.current_game
    print(f"\n=== Game {sc.current_game_index + 1}/{sc.games_total}: {next_game} ===")
    print(f"Games completed: {sc.games_completed}/{sc.games_total}")
    print(f"Running score: {sc.running_score:.2f}")

    # Regenerate dashboard with progress
    _regenerate_dashboard()

    # Auto-start next game
    cmd_start(next_game, sc.backend, sc.max_actions_per_game)


def cmd_scorecard_status():
    """Show scorecard progress and scores."""
    if not ScorecardSession.exists():
        print("Error: No active scorecard.", file=sys.stderr)
        sys.exit(1)

    sc = ScorecardSession.load()

    print(f"=== Scorecard: {sc.experiment_id} ===")
    print(f"Card ID: {sc.card_id}")
    print(f"Status: {sc.status}")
    print(f"Progress: {sc.games_completed}/{sc.games_total} games")
    print(f"Running score: {sc.running_score:.2f}")
    print()

    # Show per-game results
    for i, game_id in enumerate(sc.game_list):
        game_base = game_id.split("-")[0]
        if game_id in sc.completed_games:
            g = sc.completed_games[game_id]
            state_icon = "W" if g["state"] == "WIN" else "X" if g["state"] == "GAME_OVER" else "?"
            print(f"  [{state_icon}] {game_base:<6} levels={g['levels_completed']}  actions={g['actions']}")
        elif i == sc.current_game_index:
            print(f"  [>] {game_base:<6} (playing now)")
        else:
            print(f"  [ ] {game_base:<6}")

    # Try to get server-computed score
    try:
        backend = _create_backend("api")
        import requests
        resp = requests.get(
            f"http://localhost:5050/api/scorecard/{sc.card_id}",
            headers={"X-API-Key": os.getenv("ARC_API_KEY", "local")},
            timeout=5,
        )
        if resp.ok:
            data = resp.json()
            if "score" in data:
                print(f"\nServer-computed score: {data['score']:.2f}")
    except Exception:
        pass


def cmd_scorecard_close():
    """Close the scorecard and compute final score."""
    if not ScorecardSession.exists():
        print("Error: No active scorecard.", file=sys.stderr)
        sys.exit(1)

    # End current game if active
    if Session.exists():
        cmd_end()

    sc = ScorecardSession.load()

    # Close scorecard on server
    scorecard_data = {}
    try:
        backend = _create_backend("api")
        import requests
        resp = requests.post(
            "http://localhost:5050/api/scorecard/close",
            json={"card_id": sc.card_id},
            headers={"X-API-Key": os.getenv("ARC_API_KEY", "local")},
            timeout=10,
        )
        if resp.ok:
            scorecard_data = resp.json()
    except Exception as e:
        print(f"Warning: Could not close scorecard on server: {e}", file=sys.stderr)

    # Save full scorecard JSON
    SCORECARDS_DIR.mkdir(parents=True, exist_ok=True)
    scorecard_file = SCORECARDS_DIR / f"{sc.experiment_id}_{sc.card_id[:8]}.json"
    save_data = {
        "experiment_id": sc.experiment_id,
        "card_id": sc.card_id,
        "games_completed": sc.games_completed,
        "games_total": sc.games_total,
        "completed_games": sc.completed_games,
        "server_scorecard": scorecard_data,
    }
    with open(scorecard_file, "w") as f:
        json.dump(save_data, f, indent=2)

    # Extract final score
    final_score = scorecard_data.get("score", sc.running_score)
    total_levels = sum(g.get("levels_completed", 0) for g in sc.completed_games.values())
    total_actions = sum(g.get("actions", 0) for g in sc.completed_games.values())

    # Log to experiments/log.md
    _log_scorecard(sc, final_score, total_levels, total_actions)

    # Print final results
    print(f"\n{'='*50}")
    print(f"=== SCORECARD CLOSED: {sc.experiment_id} ===")
    print(f"{'='*50}")
    print(f"Final Score: {final_score:.2f}")
    print(f"Games: {sc.games_completed}/{sc.games_total}")
    print(f"Total Levels Completed: {total_levels}")
    print(f"Total Actions: {total_actions}")
    print(f"Saved: {scorecard_file}")

    # Regenerate dashboard
    _regenerate_dashboard()

    # Clean up
    sc.delete()
    print(f"\nScorecard complete.")


def _next_experiment_number() -> int:
    """Get the next experiment number from log.md."""
    log_path = Path("experiments/log.md")
    if not log_path.exists():
        return 1
    text = log_path.read_text()
    exp_num = 0
    for line in text.split("\n"):
        if line.startswith("|") and "SC" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts and parts[0].startswith("SC"):
                try:
                    num = int(parts[0][2:])
                    exp_num = max(exp_num, num)
                except ValueError:
                    pass
    return exp_num + 1


def _log_scorecard(sc: ScorecardSession, score: float, levels: int, actions: int):
    """Append scorecard result to experiments/log.md."""
    try:
        log_path = Path("experiments/log.md")
        if not log_path.exists():
            return
        row = (
            f"| {sc.experiment_id} | {score:.2f} | {sc.games_completed}/{sc.games_total} | "
            f"{levels}/181 | {actions} | complete | — | — |"
        )
        with open(log_path, "a") as f:
            f.write(row + "\n")
        print(f"\nLogged as {sc.experiment_id} in experiments/log.md")
    except Exception as e:
        print(f"Warning: Could not log scorecard: {e}", file=sys.stderr)


def _regenerate_dashboard():
    """Auto-regenerate the static HTML dashboard."""
    try:
        import subprocess
        subprocess.run(
            [sys.executable, "generate_dashboard.py"],
            capture_output=True, timeout=10,
        )
        print("Dashboard updated.")
    except Exception:
        pass  # Don't let dashboard failures break gameplay


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
