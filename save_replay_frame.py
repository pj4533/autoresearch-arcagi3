#!/usr/bin/env python3
"""Save a replay frame during arc CLI gameplay.

Called by the executor after each arc state --image to capture replay data.

Usage:
    uv run python save_replay_frame.py --exp 001 --game vc33 --step 1 \
        --action "click --x 32 --y 16" --reasoning "I see colored blocks..."

    # With score info
    uv run python save_replay_frame.py --exp 001 --game vc33 --step 2 \
        --action "click --x 48 --y 20" --reasoning "Testing blue button" \
        --score 0 --state NOT_FINISHED
"""

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def save_frame(exp: str, game: str, step: int, action: str, reasoning: str,
               score: int = 0, state: str = "NOT_FINISHED"):
    replays_dir = Path("experiments/replays")
    frames_dir = replays_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # Copy current frame image
    src_frame = Path(".arc_session/frame.png")
    if not src_frame.exists():
        print(f"Warning: {src_frame} not found. Run 'arc state --image' first.")
        return

    frame_filename = f"{exp}_{game}_step{step:03d}.png"
    dest_frame = frames_dir / frame_filename
    shutil.copy2(src_frame, dest_frame)

    # Append to replay JSONL
    replay_file = replays_dir / f"{exp}_{game}.jsonl"
    entry = {
        "step": step,
        "action": action,
        "reasoning": reasoning,
        "score": score,
        "state": state,
        "frame_path": f"frames/{frame_filename}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open(replay_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"Saved step {step}: {frame_filename}")


def main():
    parser = argparse.ArgumentParser(description="Save a replay frame")
    parser.add_argument("--exp", required=True, help="Experiment ID (e.g., 001)")
    parser.add_argument("--game", required=True, help="Game ID (e.g., vc33)")
    parser.add_argument("--step", required=True, type=int, help="Step number")
    parser.add_argument("--action", required=True, help="Action taken")
    parser.add_argument("--reasoning", required=True, help="Agent's reasoning")
    parser.add_argument("--score", type=int, default=0, help="Current score")
    parser.add_argument("--state", default="NOT_FINISHED", help="Game state")
    args = parser.parse_args()

    save_frame(args.exp, args.game, args.step, args.action, args.reasoning,
               args.score, args.state)


if __name__ == "__main__":
    main()
