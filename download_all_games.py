#!/usr/bin/env python3
"""Download all ARC-AGI-3 games for offline use.

Temporarily connects to the remote API to download game files,
then everything runs locally via start_local_server.py.

Usage:
    uv run python download_all_games.py
"""

import io
import json
import logging
import os
import sys

import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REMOTE_API = "https://three.arcprize.org"
ENVIRONMENTS_DIR = Path("environment_files")


def download_all_games():
    api_key = os.getenv("ARC_API_KEY")
    if not api_key:
        logger.error("ARC_API_KEY not set in .env")
        sys.exit(1)

    headers = {"X-API-Key": api_key, "Accept": "application/json"}

    # List all games from remote API
    logger.info(f"Fetching game list from {REMOTE_API}...")
    resp = requests.get(f"{REMOTE_API}/api/games", headers=headers)
    resp.raise_for_status()
    games = resp.json()
    logger.info(f"Found {len(games)} games\n")

    downloaded = 0
    skipped = 0
    failed = []

    for game_info in games:
        game_id = game_info.get("game_id", "")
        title = game_info.get("title", "Unknown")

        if "-" not in game_id:
            logger.warning(f"  Skipping {game_id} (no version hash)")
            failed.append((game_id, "no version hash"))
            continue

        base_id, version = game_id.rsplit("-", 1)
        game_dir = ENVIRONMENTS_DIR / base_id / version

        # Check if already downloaded
        if (game_dir / "metadata.json").exists() and (game_dir / f"{base_id}.py").exists():
            logger.info(f"  {title} ({game_id}) — already downloaded")
            skipped += 1
            continue

        try:
            # Fetch metadata
            meta_resp = requests.get(f"{REMOTE_API}/api/games/{base_id}", headers=headers)
            meta_resp.raise_for_status()
            metadata = meta_resp.json()

            # Fetch source code
            src_resp = requests.get(f"{REMOTE_API}/api/games/{game_id}/source", headers=headers)
            src_resp.raise_for_status()
            source_code = src_resp.text

            # Save to disk
            game_dir.mkdir(parents=True, exist_ok=True)

            # Build metadata file matching arc_agi format
            meta_file = {
                "game_id": game_id,
                "title": title,
                "default_fps": metadata.get("default_fps", 8),
                "baseline_actions": metadata.get("baseline_actions", []),
                "tags": metadata.get("tags", []),
                "local_dir": str(game_dir),
                "date_downloaded": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
            }

            (game_dir / "metadata.json").write_text(json.dumps(meta_file, indent=2))
            (game_dir / f"{base_id}.py").write_text(source_code)

            logger.info(f"  {title} ({game_id}) — downloaded")
            downloaded += 1

        except Exception as e:
            logger.error(f"  {title} ({game_id}) — FAILED: {e}")
            failed.append((game_id, str(e)))

    logger.info(f"\n{'='*50}")
    logger.info(f"Downloaded: {downloaded}")
    logger.info(f"Already had: {skipped}")
    logger.info(f"Failed: {len(failed)}")
    logger.info(f"Total available: {len(games)}")

    if failed:
        logger.info(f"\nFailed:")
        for gid, err in failed:
            logger.info(f"  {gid}: {err}")

    # Verify offline loading
    logger.info(f"\nVerifying offline mode...")
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        from arc_agi import Arcade, OperationMode
        arcade = Arcade(operation_mode=OperationMode.OFFLINE)
        envs = arcade.get_environments()
    finally:
        sys.stdout = old_stdout

    logger.info(f"Offline mode sees {len(envs)} games:")
    for e in envs:
        logger.info(f"  {e.game_id} — {e.title}")


if __name__ == "__main__":
    download_all_games()
