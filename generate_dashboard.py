#!/usr/bin/env python3
"""
Generate a static HTML dashboard from scorecard-based experiments.

Reads:
  - experiments/log.md          (per-scorecard summary table)
  - experiments/scorecards/*.json (per-scorecard detail JSON)
  - .arc_session/scorecard.json  (live scorecard in progress)
  - experiments/replays/*.jsonl   (frame-by-frame replays)

Usage:
    uv run python generate_dashboard.py
    uv run python generate_dashboard.py --log experiments/log.md --output experiments/dashboard.html
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ALL_GAMES = [
    "ar25", "bp35", "cd82", "cn04", "dc22",
    "ft09", "g50t", "ka59", "lf52", "lp85",
    "ls20", "m0r0", "r11l", "re86", "s5i5",
    "sb26", "sc25", "sk48", "sp80", "su15",
    "tn36", "tr87", "tu93", "vc33", "wa30",
]


def parse_log(log_path: str) -> list[dict]:
    """Parse experiments/log.md scorecard table into list of dicts.

    Expected format:
    | Exp | Score | Games | Levels | Actions | Status | Strategy | Notes |
    """
    path = Path(log_path)
    if not path.exists():
        return []

    text = path.read_text()
    scorecards = []

    lines = text.strip().split("\n")
    in_table = False
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            in_table = False
            continue

        # Detect header row
        if "Exp" in line and "Score" in line and "Strategy" in line:
            in_table = True
            continue
        # Skip separator
        if re.match(r"^\|[\s\-|]+\|$", line):
            continue
        if not in_table:
            continue

        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c != ""]

        if len(cells) < 7:
            continue

        try:
            # Parse "25/25" style games field
            games_str = cells[2].strip()
            games_completed = 0
            games_total = 25
            if "/" in games_str:
                parts = games_str.split("/")
                games_completed = int(parts[0])
                games_total = int(parts[1])
            elif games_str.isdigit():
                games_completed = int(games_str)

            # Parse levels field
            levels_str = cells[3].strip()
            levels_completed = 0
            levels_total = 0
            if "/" in levels_str:
                parts = levels_str.split("/")
                levels_completed = int(parts[0])
                levels_total = int(parts[1])
            elif levels_str.isdigit():
                levels_completed = int(levels_str)

            sc = {
                "id": cells[0].strip(),
                "score": float(cells[1]) if cells[1].strip() else 0.0,
                "games_completed": games_completed,
                "games_total": games_total,
                "levels_completed": levels_completed,
                "levels_total": levels_total,
                "actions": int(cells[4]) if cells[4].strip() else 0,
                "status": cells[5].strip().lower(),
                "strategy": cells[6].strip(),
                "notes": cells[7].strip() if len(cells) > 7 else "",
            }
            scorecards.append(sc)
        except (ValueError, IndexError):
            continue

    return scorecards


def load_scorecard_details(scorecards_dir: str) -> dict:
    """Load per-scorecard detail JSON files from experiments/scorecards/."""
    path = Path(scorecards_dir)
    if not path.exists():
        return {}

    details = {}
    for json_file in sorted(path.glob("*.json")):
        try:
            with open(json_file) as f:
                data = json.load(f)
            exp_id = data.get("experiment_id", json_file.stem)
            details[exp_id] = data
        except (json.JSONDecodeError, OSError):
            continue

    return details


def load_live_scorecard(session_path: str) -> dict | None:
    """Load live scorecard from .arc_session/scorecard.json if it exists."""
    path = Path(session_path)
    if not path.exists():
        return None

    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def scan_replays(replays_dir: str) -> list[dict]:
    """Scan experiments/replays/*.jsonl for available replays."""
    path = Path(replays_dir)
    if not path.exists():
        return []

    replays = []
    for jsonl_file in sorted(path.glob("*.jsonl")):
        name = jsonl_file.stem
        # Format: {exp_id}_{game_id} or similar
        parts = name.rsplit("_", 1)
        if len(parts) != 2:
            exp_id = name
            game_id = "unknown"
        else:
            exp_id, game_id = parts

        steps = []
        try:
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        steps.append(json.loads(line))
        except (json.JSONDecodeError, OSError):
            continue

        if not steps:
            continue

        final_score = steps[-1].get("score", 0)
        replays.append({
            "exp_id": exp_id,
            "game_id": game_id,
            "filename": jsonl_file.name,
            "num_steps": len(steps),
            "final_score": final_score,
            "steps": steps,
        })

    return replays


def build_data(
    scorecards: list[dict],
    scorecard_details: dict,
    live_scorecard: dict | None,
    replays: list[dict],
) -> dict:
    """Build dashboard data from all sources."""
    completed = [sc for sc in scorecards if sc["status"] == "complete"]

    best_score = 0.0
    best_sc = "none"
    total_levels = 0
    for sc in scorecards:
        if sc["score"] > best_score:
            best_score = sc["score"]
            best_sc = sc["id"]
        total_levels += sc["levels_completed"]

    # Per-game scores across all scorecards (from detail files)
    per_game_matrix = {}  # {sc_id: {game: score}}
    for sc_id, detail in scorecard_details.items():
        per_game_matrix[sc_id] = {}
        completed_games = detail.get("completed_games", {})
        for game_key, game_data in completed_games.items():
            # game_key may be like "ar25-e3c63847" or just "ar25"
            game_short = game_key.split("-")[0] if "-" in game_key else game_key
            score = game_data.get("score", 0)
            per_game_matrix[sc_id][game_short] = {
                "score": score,
                "actions": game_data.get("actions", 0),
                "levels_completed": game_data.get("levels_completed", 0),
                "state": game_data.get("state", ""),
            }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scorecards": scorecards,
        "scorecard_details": scorecard_details,
        "per_game_matrix": per_game_matrix,
        "live_scorecard": live_scorecard,
        "all_games": ALL_GAMES,
        "summary": {
            "total_scorecards": len(scorecards),
            "completed_scorecards": len(completed),
            "best_score": best_score,
            "best_scorecard": best_sc,
            "total_levels": total_levels,
        },
        "replays": replays,
    }


def generate_html(data: dict) -> str:
    """Generate self-contained HTML dashboard."""
    # Strip step data from replays for the replay list (keep it lightweight)
    replay_list = []
    for r in data["replays"]:
        replay_list.append({
            "exp_id": r["exp_id"],
            "game_id": r["game_id"],
            "filename": r["filename"],
            "num_steps": r["num_steps"],
            "final_score": r["final_score"],
        })

    # Full replay data (with steps) embedded separately
    replay_data = {}
    for r in data["replays"]:
        key = f"{r['exp_id']}_{r['game_id']}"
        replay_data[key] = r["steps"]

    # Clean scorecard details for JSON embedding (remove huge server_scorecard if present)
    clean_details = {}
    for sc_id, detail in data["scorecard_details"].items():
        clean = {k: v for k, v in detail.items() if k != "server_scorecard"}
        clean_details[sc_id] = clean

    data_json = json.dumps({
        "summary": data["summary"],
        "scorecards": data["scorecards"],
        "scorecard_details": clean_details,
        "per_game_matrix": data["per_game_matrix"],
        "live_scorecard": data["live_scorecard"],
        "all_games": data["all_games"],
        "generated_at": data["generated_at"],
        "replay_list": replay_list,
    })

    replay_json = json.dumps(replay_data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARC-AGI-3 Scorecard Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-deep: #0f172a;
    --bg-card: #1e293b;
    --bg-card-hover: #253349;
    --border: #334155;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-green: #22c55e;
    --accent-red: #ef4444;
    --accent-blue: #3b82f6;
    --accent-amber: #fbbf24;
    --accent-violet: #a78bfa;
    --accent-cyan: #22d3ee;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: var(--bg-deep);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    min-height: 100vh;
  }}

  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-card);
  }}

  .header h1 {{
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.01em;
  }}

  .header-right {{
    display: flex;
    align-items: center;
    gap: 16px;
  }}

  .tabs {{
    display: flex;
    gap: 4px;
    background: var(--bg-deep);
    border-radius: 8px;
    padding: 3px;
  }}

  .tab {{
    padding: 6px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
    transition: all 0.15s;
    border: none;
    background: none;
    font-family: inherit;
  }}

  .tab:hover {{ color: var(--text-primary); }}
  .tab.active {{
    background: var(--bg-card);
    color: var(--text-primary);
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }}

  .timer {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--text-muted);
  }}

  .live-dot {{
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent-green);
    margin-right: 4px;
    animation: pulse 2s infinite;
  }}

  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
  }}

  .content {{ padding: 20px 24px; }}

  .stats {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }}

  .stat-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }}

  .stat-value {{
    font-size: 28px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -0.02em;
  }}

  .stat-label {{
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  .stat-value.green {{ color: var(--accent-green); }}
  .stat-value.red {{ color: var(--accent-red); }}
  .stat-value.blue {{ color: var(--accent-blue); }}
  .stat-value.amber {{ color: var(--accent-amber); }}
  .stat-value.cyan {{ color: var(--accent-cyan); }}
  .stat-value.violet {{ color: var(--accent-violet); }}

  .chart-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
  }}

  .chart-title {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
  }}

  /* Live scorecard banner */
  .live-banner {{
    background: var(--bg-card);
    border: 1px solid var(--accent-amber);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
  }}

  .live-banner-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }}

  .live-banner-title {{
    font-size: 14px;
    font-weight: 600;
    color: var(--accent-amber);
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  .live-banner-stats {{
    display: flex;
    gap: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
  }}

  .live-grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 6px;
  }}

  .live-cell {{
    aspect-ratio: 1;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    border: 1px solid var(--border);
    transition: all 0.2s;
  }}

  .live-cell.completed-scored {{
    background: rgba(34, 197, 94, 0.25);
    border-color: var(--accent-green);
    color: var(--accent-green);
  }}

  .live-cell.completed-zero {{
    background: rgba(100, 116, 139, 0.15);
    border-color: var(--text-muted);
    color: var(--text-muted);
  }}

  .live-cell.current {{
    background: rgba(251, 191, 36, 0.2);
    border-color: var(--accent-amber);
    color: var(--accent-amber);
    animation: pulse 2s infinite;
  }}

  .live-cell.pending {{
    background: rgba(15, 23, 42, 0.5);
    border-color: rgba(51, 65, 85, 0.5);
    color: var(--text-muted);
    opacity: 0.4;
  }}

  /* Game grid for progress tab */
  .game-grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
  }}

  .game-cell {{
    background: var(--bg-deep);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }}

  .game-cell.scored {{ border-color: var(--accent-green); background: rgba(34,197,94,0.05); }}
  .game-cell.attempted {{ border-color: var(--accent-blue); }}
  .game-cell .game-name {{ font-weight: 600; margin-bottom: 4px; }}
  .game-cell .game-score {{ color: var(--text-secondary); font-size: 11px; }}

  /* Heatmap container */
  .heatmap-container {{
    overflow-x: auto;
  }}

  /* Detail view */
  .detail-layout {{
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 16px;
    height: calc(100vh - 180px);
  }}

  .sc-list {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow-y: auto;
  }}

  .sc-list-header {{
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    position: sticky;
    top: 0;
    background: var(--bg-card);
    z-index: 1;
  }}

  .sc-list-item {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.1s;
    font-size: 13px;
  }}

  .sc-list-item:hover {{ background: var(--bg-card-hover); }}
  .sc-list-item.selected {{ background: var(--bg-card-hover); border-left: 3px solid var(--accent-blue); }}

  .sc-list-item .sc-id {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 12px;
  }}

  .sc-list-item .sc-meta {{
    color: var(--text-secondary);
    font-size: 11px;
    margin-top: 3px;
    display: flex;
    gap: 12px;
  }}

  .detail-panel {{
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
  }}

  .detail-section {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }}

  .detail-section h3 {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
  }}

  .detail-row {{
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid rgba(51,65,85,0.5);
    font-size: 13px;
  }}

  .detail-row:last-child {{ border-bottom: none; }}
  .detail-label {{ color: var(--text-secondary); }}
  .detail-value {{ font-family: 'JetBrains Mono', monospace; font-weight: 500; }}

  .detail-game-grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
    margin-bottom: 16px;
  }}

  .detail-game-cell {{
    border-radius: 8px;
    padding: 10px 8px;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    border: 1px solid var(--border);
  }}

  .detail-game-cell .dg-name {{
    font-size: 11px;
    font-weight: 600;
    margin-bottom: 4px;
  }}

  .detail-game-cell .dg-score {{
    font-size: 16px;
    font-weight: 700;
  }}

  .detail-game-cell .dg-meta {{
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 2px;
  }}

  .detail-game-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }}

  .detail-game-table th {{
    text-align: left;
    padding: 8px 10px;
    border-bottom: 1px solid var(--border);
    color: var(--text-secondary);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 11px;
  }}

  .detail-game-table td {{
    padding: 7px 10px;
    border-bottom: 1px solid rgba(51,65,85,0.3);
    font-family: 'JetBrains Mono', monospace;
  }}

  .detail-game-table tr:hover {{
    background: var(--bg-card-hover);
  }}

  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
  }}

  .badge-complete {{ background: rgba(34,197,94,0.15); color: var(--accent-green); }}
  .badge-running {{ background: rgba(251,191,36,0.15); color: var(--accent-amber); }}
  .badge-failed {{ background: rgba(239,68,68,0.15); color: var(--accent-red); }}
  .badge-pending {{ background: rgba(100,116,139,0.15); color: var(--text-muted); }}

  .view {{ display: none; }}
  .view.active {{ display: block; }}

  .empty-state {{
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
  }}

  .empty-state h2 {{
    font-size: 16px;
    margin-bottom: 8px;
    color: var(--text-secondary);
  }}

  /* Replay view */
  .replay-layout {{
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 16px;
    height: calc(100vh - 180px);
  }}

  .replay-list {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow-y: auto;
  }}

  .replay-list-header {{
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    position: sticky;
    top: 0;
    background: var(--bg-card);
    z-index: 1;
  }}

  .replay-list-item {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.1s;
    font-size: 13px;
  }}

  .replay-list-item:hover {{ background: var(--bg-card-hover); }}
  .replay-list-item.selected {{ background: var(--bg-card-hover); border-left: 3px solid var(--accent-violet); }}

  .replay-list-item .replay-title {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 12px;
  }}

  .replay-list-item .replay-meta {{
    color: var(--text-secondary);
    font-size: 11px;
    margin-top: 3px;
    display: flex;
    gap: 12px;
  }}

  .replay-viewer {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    height: 100%;
    overflow: hidden;
  }}

  .replay-main {{
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 16px;
    flex: 1;
    min-height: 0;
  }}

  .replay-frame {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    position: relative;
  }}

  .replay-frame img {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    image-rendering: pixelated;
  }}

  .replay-info {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}

  .replay-info-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}

  .replay-step-counter {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 600;
  }}

  .replay-score {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: var(--accent-amber);
  }}

  .replay-action {{
    background: var(--bg-deep);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px;
  }}

  .replay-action-label {{
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }}

  .replay-action-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--accent-cyan);
  }}

  .replay-reasoning {{
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
    flex: 1;
    overflow-y: auto;
  }}

  .replay-reasoning-label {{
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }}

  .replay-controls {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .replay-controls button {{
    background: var(--bg-deep);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-primary);
    padding: 6px 14px;
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.15s;
  }}

  .replay-controls button:hover {{
    background: var(--bg-card-hover);
    border-color: var(--accent-blue);
  }}

  .replay-controls button:disabled {{
    opacity: 0.4;
    cursor: not-allowed;
  }}

  .replay-controls button.playing {{
    background: rgba(239,68,68,0.15);
    border-color: var(--accent-red);
    color: var(--accent-red);
  }}

  .replay-slider {{
    flex: 1;
    -webkit-appearance: none;
    appearance: none;
    height: 4px;
    border-radius: 2px;
    background: var(--border);
    outline: none;
  }}

  .replay-slider::-webkit-slider-thumb {{
    -webkit-appearance: none;
    appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--accent-blue);
    cursor: pointer;
  }}

  .replay-slider::-moz-range-thumb {{
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--accent-blue);
    cursor: pointer;
    border: none;
  }}

  .replay-step-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
    min-width: 60px;
    text-align: right;
  }}

  .game-badge {{
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    background: rgba(59,130,246,0.15);
    color: var(--accent-blue);
    margin-right: 4px;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>ARC-AGI-3 Scorecard Dashboard</h1>
  <div class="header-right">
    <div class="tabs">
      <button class="tab active" onclick="switchView('progress')">Progress</button>
      <button class="tab" onclick="switchView('scorecard-detail')">Scorecard Detail</button>
      <button class="tab" onclick="switchView('replays')">Replays</button>
    </div>
    <div class="timer"><span class="live-dot"></span><span id="countdown">30</span>s</div>
  </div>
</div>

<div class="content">
  <!-- Progress View -->
  <div id="progress-view" class="view active">
    <div id="live-banner-container"></div>

    <div class="stats">
      <div class="stat-card">
        <div class="stat-value blue" id="stat-scorecards">0</div>
        <div class="stat-label">Scorecards Run</div>
      </div>
      <div class="stat-card">
        <div class="stat-value amber" id="stat-best-score">0.00</div>
        <div class="stat-label">Best Aggregate Score</div>
      </div>
      <div class="stat-card">
        <div class="stat-value green" id="stat-total-levels">0</div>
        <div class="stat-label">Total Levels Solved</div>
      </div>
      <div class="stat-card">
        <div class="stat-value cyan" id="stat-best-sc">---</div>
        <div class="stat-label">Best Scorecard</div>
      </div>
    </div>

    <div class="chart-card">
      <div class="chart-title">Score History</div>
      <div id="score-history-chart"></div>
    </div>

    <div class="chart-card">
      <div class="chart-title">Per-Game Heatmap</div>
      <div class="heatmap-container" id="heatmap-chart"></div>
    </div>
  </div>

  <!-- Scorecard Detail View -->
  <div id="scorecard-detail-view" class="view">
    <div class="detail-layout">
      <div class="sc-list" id="sc-list">
        <div class="sc-list-header">Scorecards</div>
      </div>
      <div class="detail-panel" id="sc-detail-panel">
        <div class="empty-state">
          <h2>Select a scorecard</h2>
          <p>Click a scorecard on the left to view per-game details</p>
        </div>
      </div>
    </div>
  </div>

  <!-- Replays View -->
  <div id="replays-view" class="view">
    <div class="replay-layout">
      <div class="replay-list" id="replay-list">
        <div class="replay-list-header">Available Replays</div>
      </div>
      <div id="replay-panel">
        <div class="empty-state">
          <h2>Select a replay</h2>
          <p>Click a replay on the left to view the step-by-step playback</p>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const DATA = {data_json};
const REPLAY_DATA = {replay_json};

let countdown = 30;
let selectedSC = null;
let selectedReplay = null;
let replayInterval = null;
let currentStep = 0;

const ALL_GAMES = DATA.all_games;

// Score color: 0 = dark gray, higher = brighter green
function scoreColor(score) {{
  if (score <= 0) return 'rgba(100, 116, 139, 0.2)';
  // Scale from dim green to bright green
  const intensity = Math.min(1, score / 20);  // 20+ is very bright
  const r = Math.round(34 + (34 - 34) * intensity);
  const g = Math.round(80 + (197 - 80) * intensity);
  const b = Math.round(40 + (94 - 40) * intensity);
  const a = 0.3 + 0.7 * intensity;
  return `rgba(${{r}}, ${{g}}, ${{b}}, ${{a}})`;
}}

function scoreBorderColor(score) {{
  if (score <= 0) return 'var(--text-muted)';
  const intensity = Math.min(1, score / 20);
  return `rgba(34, 197, 94, ${{0.3 + 0.7 * intensity}})`;
}}

function statusBadgeClass(status) {{
  if (status === 'complete') return 'badge-complete';
  if (status === 'running') return 'badge-running';
  if (status === 'failed') return 'badge-failed';
  return 'badge-pending';
}}

// ==============================
// Progress Tab
// ==============================

function renderLiveBanner() {{
  const container = document.getElementById('live-banner-container');
  const live = DATA.live_scorecard;

  if (!live) {{
    container.innerHTML = '';
    return;
  }}

  // Determine completed/current/pending games
  const completedGames = live.completed_games || {{}};
  const currentGame = live.current_game || null;
  const completedSet = new Set(Object.keys(completedGames).map(k => k.split('-')[0]));

  let gamesCompleted = Object.keys(completedGames).length;
  let gamesTotal = live.games_total || 25;
  let runningScore = live.running_score || live.score || 0;

  let gridHtml = '';
  ALL_GAMES.forEach(game => {{
    let cellClass = 'pending';
    let cellText = game;

    // Check if this game is in completed games (may have full key like "ar25-e3c63847")
    let matchedKey = null;
    for (const key of Object.keys(completedGames)) {{
      if (key.startsWith(game)) {{
        matchedKey = key;
        break;
      }}
    }}

    if (matchedKey) {{
      const gd = completedGames[matchedKey];
      const score = gd.score || 0;
      const levels = gd.levels_completed || 0;
      if (score > 0 || levels > 0) {{
        cellClass = 'completed-scored';
        cellText = game + '<br><span style="font-size:9px">' + score.toFixed(1) + '</span>';
      }} else {{
        cellClass = 'completed-zero';
      }}
    }} else if (currentGame && currentGame.startsWith(game)) {{
      cellClass = 'current';
    }}

    gridHtml += `<div class="live-cell ${{cellClass}}">${{cellText}}</div>`;
  }});

  container.innerHTML = `
    <div class="live-banner">
      <div class="live-banner-header">
        <div class="live-banner-title">
          <span class="live-dot"></span> Live Scorecard In Progress
        </div>
        <div class="live-banner-stats">
          <span style="color:var(--accent-amber)">Score: ${{typeof runningScore === 'number' ? runningScore.toFixed(2) : runningScore}}</span>
          <span style="color:var(--text-secondary)">Games: ${{gamesCompleted}} / ${{gamesTotal}}</span>
        </div>
      </div>
      <div class="live-grid">${{gridHtml}}</div>
    </div>
  `;
}}

function renderStats() {{
  const s = DATA.summary;
  document.getElementById('stat-scorecards').textContent = s.total_scorecards;
  document.getElementById('stat-best-score').textContent = s.best_score.toFixed(2);
  document.getElementById('stat-total-levels').textContent = s.total_levels;
  document.getElementById('stat-best-sc').textContent = s.best_scorecard;
}}

function renderScoreHistory() {{
  const scs = DATA.scorecards;
  if (scs.length === 0) {{
    document.getElementById('score-history-chart').innerHTML = '<div class="empty-state"><p>No scorecards yet</p></div>';
    return;
  }}

  const trace = {{
    x: scs.map(sc => sc.id),
    y: scs.map(sc => sc.score),
    mode: 'markers+lines',
    type: 'scatter',
    line: {{ color: '#3b82f6', width: 2 }},
    marker: {{
      color: scs.map(sc => sc.score > 0 ? '#22c55e' : '#64748b'),
      size: 10,
      line: {{ color: '#0f172a', width: 1.5 }},
    }},
    text: scs.map(sc => `${{sc.id}}<br>Score: ${{sc.score.toFixed(2)}}<br>Levels: ${{sc.levels_completed}}<br>Strategy: ${{sc.strategy}}`),
    hovertemplate: '%{{text}}<extra></extra>',
  }};

  Plotly.react('score-history-chart', [trace], {{
    template: 'plotly_dark',
    paper_bgcolor: 'transparent',
    plot_bgcolor: '#1e293b',
    height: 300,
    margin: {{ l: 50, r: 20, t: 10, b: 60 }},
    xaxis: {{
      title: {{ text: 'Scorecard', font: {{ size: 12, color: '#94a3b8' }} }},
      gridcolor: '#334155',
      tickfont: {{ family: 'JetBrains Mono', size: 10, color: '#94a3b8' }},
      tickangle: -45,
    }},
    yaxis: {{
      title: {{ text: 'Aggregate Score', font: {{ size: 12, color: '#94a3b8' }} }},
      gridcolor: '#334155',
      tickfont: {{ family: 'JetBrains Mono', size: 10, color: '#94a3b8' }},
      rangemode: 'tozero',
    }},
    showlegend: false,
  }}, {{ responsive: true, displayModeBar: false }});
}}

function renderHeatmap() {{
  const matrix = DATA.per_game_matrix;
  const scIds = Object.keys(matrix);

  if (scIds.length === 0) {{
    document.getElementById('heatmap-chart').innerHTML = '<div class="empty-state"><p>No per-game data available yet</p></div>';
    return;
  }}

  // Sort scorecard IDs to match log order
  const orderedIds = DATA.scorecards.map(sc => sc.id).filter(id => matrix[id]);

  // Build z-matrix: rows = scorecards, cols = games (alphabetical = ALL_GAMES)
  const z = [];
  const textMatrix = [];
  orderedIds.forEach(scId => {{
    const row = [];
    const textRow = [];
    ALL_GAMES.forEach(game => {{
      const gd = matrix[scId] && matrix[scId][game];
      const score = gd ? gd.score : 0;
      row.push(score);
      if (gd) {{
        textRow.push(`${{scId}} / ${{game}}<br>Score: ${{score.toFixed(2)}}<br>Levels: ${{gd.levels_completed}}<br>Actions: ${{gd.actions}}`);
      }} else {{
        textRow.push(`${{scId}} / ${{game}}<br>No data`);
      }}
    }});
    z.push(row);
    textMatrix.push(textRow);
  }});

  const trace = {{
    z: z,
    x: ALL_GAMES,
    y: orderedIds,
    type: 'heatmap',
    colorscale: [
      [0, '#1e293b'],
      [0.01, '#1a3a2a'],
      [0.25, '#166534'],
      [0.5, '#16a34a'],
      [0.75, '#22c55e'],
      [1, '#4ade80'],
    ],
    text: textMatrix,
    hovertemplate: '%{{text}}<extra></extra>',
    showscale: true,
    colorbar: {{
      title: {{ text: 'Score', font: {{ color: '#94a3b8', size: 11 }} }},
      tickfont: {{ color: '#94a3b8', size: 10, family: 'JetBrains Mono' }},
      bgcolor: 'transparent',
      borderwidth: 0,
    }},
  }};

  const height = Math.max(250, orderedIds.length * 30 + 80);

  Plotly.react('heatmap-chart', [trace], {{
    template: 'plotly_dark',
    paper_bgcolor: 'transparent',
    plot_bgcolor: '#1e293b',
    height: height,
    margin: {{ l: 70, r: 80, t: 10, b: 60 }},
    xaxis: {{
      tickfont: {{ family: 'JetBrains Mono', size: 10, color: '#94a3b8' }},
      tickangle: -45,
      side: 'bottom',
    }},
    yaxis: {{
      tickfont: {{ family: 'JetBrains Mono', size: 10, color: '#94a3b8' }},
      autorange: 'reversed',
    }},
  }}, {{ responsive: true, displayModeBar: false }});
}}

// ==============================
// Scorecard Detail Tab
// ==============================

function renderSCList() {{
  const list = document.getElementById('sc-list');
  list.innerHTML = '<div class="sc-list-header">Scorecards (' + DATA.scorecards.length + ')</div>';

  if (DATA.scorecards.length === 0) {{
    const div = document.createElement('div');
    div.style.cssText = 'padding:40px 20px;text-align:center;color:var(--text-muted);font-size:13px';
    div.textContent = 'No scorecards recorded yet';
    list.appendChild(div);
    return;
  }}

  // Show newest first
  const reversed = [...DATA.scorecards].reverse();
  reversed.forEach(sc => {{
    const div = document.createElement('div');
    div.className = 'sc-list-item' + (selectedSC === sc.id ? ' selected' : '');
    const badgeClass = statusBadgeClass(sc.status);
    div.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span class="sc-id">${{sc.id}}</span>
        <span>
          <span class="badge ${{badgeClass}}">${{sc.status}}</span>
          <span style="font-family:JetBrains Mono;color:var(--accent-amber);font-size:12px;margin-left:6px">${{sc.score.toFixed(2)}}</span>
        </span>
      </div>
      <div class="sc-meta">
        <span>Games: ${{sc.games_completed}}/${{sc.games_total}}</span>
        <span>Levels: ${{sc.levels_completed}}</span>
        <span>Actions: ${{sc.actions}}</span>
      </div>
    `;
    div.onclick = () => selectScorecard(sc.id);
    list.appendChild(div);
  }});
}}

function selectScorecard(scId) {{
  selectedSC = scId;
  renderSCList();

  const sc = DATA.scorecards.find(s => s.id === scId);
  if (!sc) return;

  const panel = document.getElementById('sc-detail-panel');
  const detail = DATA.scorecard_details[scId];
  const gameMatrix = DATA.per_game_matrix[scId] || {{}};

  // Build 5x5 game grid with color-coded scores
  let gridHtml = '';
  ALL_GAMES.forEach(game => {{
    const gd = gameMatrix[game];
    const score = gd ? gd.score : null;
    const levels = gd ? gd.levels_completed : 0;
    const actions = gd ? gd.actions : 0;

    let bgColor, borderColor, textColor;
    if (score === null) {{
      bgColor = 'var(--bg-deep)';
      borderColor = 'rgba(51,65,85,0.5)';
      textColor = 'var(--text-muted)';
    }} else if (score > 0) {{
      bgColor = scoreColor(score);
      borderColor = scoreBorderColor(score);
      textColor = 'var(--accent-green)';
    }} else {{
      bgColor = 'rgba(100,116,139,0.1)';
      borderColor = 'var(--text-muted)';
      textColor = 'var(--text-muted)';
    }}

    gridHtml += `
      <div class="detail-game-cell" style="background:${{bgColor}};border-color:${{borderColor}}">
        <div class="dg-name" style="color:${{textColor}}">${{game}}</div>
        <div class="dg-score" style="color:${{textColor}}">${{score !== null ? score.toFixed(1) : '---'}}</div>
        <div class="dg-meta">${{score !== null ? `L:${{levels}} A:${{actions}}` : ''}}</div>
      </div>
    `;
  }});

  // Build per-game table rows
  let tableHtml = '';
  const sortedGames = [...ALL_GAMES].filter(g => gameMatrix[g]);
  // Sort by score descending
  sortedGames.sort((a, b) => (gameMatrix[b]?.score || 0) - (gameMatrix[a]?.score || 0));

  sortedGames.forEach(game => {{
    const gd = gameMatrix[game];
    const scoreVal = gd.score || 0;
    const scoreStyle = scoreVal > 0 ? 'color:var(--accent-green)' : 'color:var(--text-muted)';

    // Check for matching replay
    let replayLink = '';
    const matchingReplay = DATA.replay_list.find(r => r.exp_id === scId && r.game_id === game);
    if (matchingReplay) {{
      replayLink = `<span style="color:var(--accent-violet);cursor:pointer;font-size:10px" onclick="event.stopPropagation();switchView('replays');setTimeout(()=>openReplayByKey('${{scId}}_${{game}}'),100)">replay</span>`;
    }}

    tableHtml += `
      <tr>
        <td style="font-weight:600">${{game}}</td>
        <td style="${{scoreStyle}}">${{scoreVal.toFixed(2)}}</td>
        <td>${{gd.levels_completed || 0}}</td>
        <td>${{gd.actions || 0}}</td>
        <td style="color:var(--text-muted)">${{gd.state || ''}}</td>
        <td>${{replayLink}}</td>
      </tr>
    `;
  }});

  // Games with no data
  const unplayed = ALL_GAMES.filter(g => !gameMatrix[g]);
  unplayed.forEach(game => {{
    tableHtml += `
      <tr style="opacity:0.4">
        <td>${{game}}</td>
        <td>---</td>
        <td>---</td>
        <td>---</td>
        <td></td>
        <td></td>
      </tr>
    `;
  }});

  panel.innerHTML = `
    <div class="detail-section">
      <h3>${{sc.id}} <span class="badge ${{statusBadgeClass(sc.status)}}" style="margin-left:8px">${{sc.status}}</span></h3>
      <div class="detail-row"><span class="detail-label">Aggregate Score</span><span class="detail-value" style="color:var(--accent-amber)">${{sc.score.toFixed(2)}}</span></div>
      <div class="detail-row"><span class="detail-label">Games</span><span class="detail-value">${{sc.games_completed}} / ${{sc.games_total}}</span></div>
      <div class="detail-row"><span class="detail-label">Levels Completed</span><span class="detail-value">${{sc.levels_completed}}${{sc.levels_total ? ' / ' + sc.levels_total : ''}}</span></div>
      <div class="detail-row"><span class="detail-label">Total Actions</span><span class="detail-value">${{sc.actions}}</span></div>
      <div class="detail-row"><span class="detail-label">Strategy</span><span class="detail-value" style="font-size:12px;max-width:60%;text-align:right">${{sc.strategy}}</span></div>
      ${{sc.notes ? `<div class="detail-row"><span class="detail-label">Notes</span><span style="font-size:12px;color:var(--text-secondary);max-width:60%;text-align:right">${{sc.notes}}</span></div>` : ''}}
    </div>
    <div class="detail-section">
      <h3>Game Grid</h3>
      <div class="detail-game-grid">${{gridHtml}}</div>
    </div>
    <div class="detail-section">
      <h3>Per-Game Results (${{sortedGames.length}} games)</h3>
      <table class="detail-game-table">
        <thead>
          <tr>
            <th>Game</th>
            <th>Score</th>
            <th>Levels</th>
            <th>Actions</th>
            <th>State</th>
            <th></th>
          </tr>
        </thead>
        <tbody>${{tableHtml}}</tbody>
      </table>
    </div>
  `;
}}

// ==============================
// Replays Tab
// ==============================

function renderReplayList() {{
  const list = document.getElementById('replay-list');
  list.innerHTML = '<div class="replay-list-header">Available Replays (' + DATA.replay_list.length + ')</div>';

  if (DATA.replay_list.length === 0) {{
    const div = document.createElement('div');
    div.style.cssText = 'padding:40px 20px;text-align:center;color:var(--text-muted);font-size:13px';
    div.textContent = 'No replays found in experiments/replays/';
    list.appendChild(div);
    return;
  }}

  DATA.replay_list.forEach(r => {{
    const key = r.exp_id + '_' + r.game_id;
    const div = document.createElement('div');
    div.className = 'replay-list-item' + (selectedReplay === key ? ' selected' : '');
    div.setAttribute('data-key', key);
    div.innerHTML = `
      <div class="replay-title">${{r.exp_id}} <span class="game-badge">${{r.game_id}}</span></div>
      <div class="replay-meta">
        <span>${{r.num_steps}} steps</span>
        <span>Score: ${{typeof r.final_score === 'number' ? r.final_score.toFixed(4) : r.final_score}}</span>
      </div>
    `;
    div.onclick = () => openReplay(key, r);
    list.appendChild(div);
  }});
}}

function openReplayByKey(key) {{
  const r = DATA.replay_list.find(x => x.exp_id + '_' + x.game_id === key);
  if (r) openReplay(key, r);
}}

function openReplay(key, replayInfo) {{
  stopPlayback();
  selectedReplay = key;
  currentStep = 0;
  renderReplayList();

  const steps = REPLAY_DATA[key];
  if (!steps || steps.length === 0) {{
    document.getElementById('replay-panel').innerHTML = '<div class="empty-state"><h2>No step data</h2><p>This replay has no steps recorded.</p></div>';
    return;
  }}

  const panel = document.getElementById('replay-panel');
  panel.innerHTML = `
    <div class="replay-viewer">
      <div class="replay-main">
        <div class="replay-frame" id="replay-frame">
          <img id="replay-img" src="" alt="Game frame" />
        </div>
        <div class="replay-info">
          <div class="replay-info-header">
            <span class="replay-step-counter" id="replay-step-counter">Step 1 / ${{steps.length}}</span>
            <span class="replay-score" id="replay-score-display">Score: 0</span>
          </div>
          <div class="replay-action">
            <div class="replay-action-label">Action</div>
            <div class="replay-action-value" id="replay-action-display">---</div>
          </div>
          <div style="flex:1;overflow-y:auto">
            <div class="replay-reasoning-label">Reasoning</div>
            <div class="replay-reasoning" id="replay-reasoning-display">---</div>
          </div>
        </div>
      </div>
      <div class="replay-controls">
        <button id="btn-prev" onclick="replayPrev()">Prev</button>
        <button id="btn-play" onclick="togglePlayback()">Play</button>
        <button id="btn-next" onclick="replayNext()">Next</button>
        <input type="range" class="replay-slider" id="replay-slider" min="0" max="${{steps.length - 1}}" value="0" oninput="replaySeek(this.value)" />
        <span class="replay-step-label" id="replay-step-label">1 / ${{steps.length}}</span>
      </div>
    </div>
  `;

  renderReplayStep(steps, 0);
}}

function renderReplayStep(steps, index) {{
  if (!steps || index < 0 || index >= steps.length) return;

  const step = steps[index];
  currentStep = index;

  const img = document.getElementById('replay-img');
  if (step.frame_path) {{
    img.src = 'replays/' + step.frame_path;
    img.style.display = 'block';
  }} else {{
    img.style.display = 'none';
  }}

  const counter = document.getElementById('replay-step-counter');
  if (counter) counter.textContent = `Step ${{index + 1}} / ${{steps.length}}`;

  const scoreEl = document.getElementById('replay-score-display');
  if (scoreEl) {{
    const scoreVal = typeof step.score === 'number' ? step.score.toFixed(4) : (step.score || '---');
    scoreEl.textContent = `Score: ${{scoreVal}}`;
  }}

  const actionEl = document.getElementById('replay-action-display');
  if (actionEl) {{
    actionEl.textContent = step.action || '---';
  }}

  const reasonEl = document.getElementById('replay-reasoning-display');
  if (reasonEl) {{
    reasonEl.textContent = step.reasoning || '(no reasoning recorded)';
  }}

  const slider = document.getElementById('replay-slider');
  if (slider) slider.value = index;

  const label = document.getElementById('replay-step-label');
  if (label) label.textContent = `${{index + 1}} / ${{steps.length}}`;

  const prevBtn = document.getElementById('btn-prev');
  const nextBtn = document.getElementById('btn-next');
  if (prevBtn) prevBtn.disabled = (index === 0);
  if (nextBtn) nextBtn.disabled = (index === steps.length - 1);
}}

function getActiveSteps() {{
  if (!selectedReplay || !REPLAY_DATA[selectedReplay]) return null;
  return REPLAY_DATA[selectedReplay];
}}

function replayPrev() {{
  const steps = getActiveSteps();
  if (!steps) return;
  if (currentStep > 0) renderReplayStep(steps, currentStep - 1);
}}

function replayNext() {{
  const steps = getActiveSteps();
  if (!steps) return;
  if (currentStep < steps.length - 1) renderReplayStep(steps, currentStep + 1);
}}

function replaySeek(index) {{
  const steps = getActiveSteps();
  if (!steps) return;
  renderReplayStep(steps, parseInt(index));
}}

function togglePlayback() {{
  const btn = document.getElementById('btn-play');
  if (replayInterval) {{
    stopPlayback();
  }} else {{
    btn.textContent = 'Pause';
    btn.classList.add('playing');
    replayInterval = setInterval(() => {{
      const steps = getActiveSteps();
      if (!steps) {{ stopPlayback(); return; }}
      if (currentStep < steps.length - 1) {{
        renderReplayStep(steps, currentStep + 1);
      }} else {{
        stopPlayback();
      }}
    }}, 1000);
  }}
}}

function stopPlayback() {{
  if (replayInterval) {{
    clearInterval(replayInterval);
    replayInterval = null;
  }}
  const btn = document.getElementById('btn-play');
  if (btn) {{
    btn.textContent = 'Play';
    btn.classList.remove('playing');
  }}
}}

// ==============================
// View Switching
// ==============================

function switchView(view) {{
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(view + '-view').classList.add('active');
  document.querySelector(`[onclick="switchView('${{view}}')"]`).classList.add('active');

  if (view === 'scorecard-detail') {{
    renderSCList();
  }} else if (view === 'replays') {{
    renderReplayList();
  }}
}}

// ==============================
// Countdown Timer (auto-refresh Progress tab only)
// ==============================

setInterval(() => {{
  countdown--;
  if (countdown <= 0) {{
    countdown = 30;
    const activeView = document.querySelector('.view.active');
    if (activeView && activeView.id === 'progress-view') {{
      location.reload();
    }}
  }}
  document.getElementById('countdown').textContent = countdown;
}}, 1000);

// ==============================
// Initial Render
// ==============================

renderLiveBanner();
renderStats();
renderScoreHistory();
renderHeatmap();
</script>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(description="Generate ARC-AGI-3 scorecard dashboard")
    parser.add_argument("--log", default="experiments/log.md", help="Path to log.md")
    parser.add_argument("--scorecards", default="experiments/scorecards", help="Path to scorecards directory")
    parser.add_argument("--live", default=".arc_session/scorecard.json", help="Path to live scorecard")
    parser.add_argument("--replays", default="experiments/replays", help="Path to replays directory")
    parser.add_argument("--output", default="experiments/dashboard.html", help="Output HTML path")
    parser.add_argument("--data-output", default="experiments/dashboard_data.json", help="Output JSON path")
    args = parser.parse_args()

    scorecards = parse_log(args.log)
    scorecard_details = load_scorecard_details(args.scorecards)
    live_scorecard = load_live_scorecard(args.live)
    replays = scan_replays(args.replays)

    data = build_data(scorecards, scorecard_details, live_scorecard, replays)

    # Write JSON data
    Path(args.data_output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.data_output, "w") as f:
        json.dump({
            "generated_at": data["generated_at"],
            "summary": data["summary"],
            "scorecards": data["scorecards"],
            "replay_count": len(replays),
        }, f, indent=2)

    # Write HTML
    html = generate_html(data)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)

    print(f"Dashboard generated: {args.output}")
    print(f"Data written: {args.data_output}")
    print(f"Scorecards: {len(scorecards)}")
    print(f"Scorecard details: {len(scorecard_details)}")
    print(f"Live scorecard: {'yes' if live_scorecard else 'no'}")
    print(f"Replays: {len(replays)}")


if __name__ == "__main__":
    main()
