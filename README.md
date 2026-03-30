# ARC-AGI-3 Autoresearch

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![ARC Prize](https://img.shields.io/badge/ARC--AGI--3-arcprize.org-orange.svg)](https://arcprize.org/)

Autonomous research system for [ARC-AGI-3](https://docs.arcprize.org/) games. Claude Code (Opus 4.6) plays all 25 games directly via CLI with vision, using a two-agent autoresearch loop to iteratively improve play strategy. Scores are tracked via scorecards directly comparable to the competition leaderboard.

**ARC-AGI-3** is a benchmark where AI agents interact with 64x64 grid environments, discovering rules through exploration and solving levels with minimal actions. No instructions are given — the agent must figure it out. All games are solvable by humans.

## How It Works

```
Researcher ──proposes generic strategies──> Executor ──plays all 25 games──> Scorecard Score ──analyze──> Researcher
```

1. **Executor** (Claude Code) — Plays games directly via `arc` CLI with vision. Opens a scorecard, plays all 25 games, closes it. The aggregate score is directly comparable to the ARC-AGI-3 leaderboard.
2. **Researcher** (Claude Code) — Analyzes scorecard results and proposes generic play strategies that work across all games.
3. **Dashboard** — Static HTML with score history, per-game heatmaps, scorecard breakdowns, and visual game replays.

Everything runs locally. No cloud API calls needed.

## Quick Start

```bash
# Install
uv sync --extra mlx

# Download all 25 games (one-time, hits remote API)
uv run python download_all_games.py

# Start local game server
uv run python start_local_server.py

# Play a game interactively
uv run arc start vc33-9851e02b --max-actions 40
uv run arc state --image
uv run arc action click --x 32 --y 16
uv run arc end

# Run a full scorecard (all 25 games)
uv run arc scorecard open --max-actions 40
# ... play each game ...
uv run arc scorecard next    # advance to next game
uv run arc scorecard close   # get final aggregate score
```

## Scoring

```
Per-level:  min(100, (baseline_actions / your_actions)² × 100)
Per-game:   Weighted average of level scores (later levels count more)
Overall:    Simple average across all 25 games
```

Match human baseline = 100%. 2x actions = 25%. 3x = 11%. Quadratic penalty — action efficiency is everything.

25 games, 181 total levels. Each game has 6-10 levels of increasing difficulty.

## Running the Autoresearch System

```bash
# Terminal 1: Local game server (all 25 games)
uv run python start_local_server.py

# Terminal 2: Dashboard
cd experiments && python3 -m http.server 8080 --bind 0.0.0.0

# Terminal 3: Executor (plays games via arc CLI with vision)
claude
# /loop 10m Read program.md. Open scorecard, play all 25 games. NEVER modify Python code.

# Terminal 4: Researcher (proposes generic play strategies)
claude
# /loop 10m Read research_program.md. Propose generic strategies, NOT code changes.
```

## Dashboard

Static HTML dashboard at `http://localhost:8080/dashboard.html` with three tabs:

- **Progress** — Score history across scorecards, 25-game heatmap, live scorecard progress
- **Scorecard Detail** — Per-game breakdown with scores, levels, actions
- **Replays** — Frame-by-frame visual replay of games with side-by-side layout

Generated automatically on `arc end` / `arc scorecard close`, or manually:
```bash
uv run python generate_dashboard.py
```

## Project Structure

```
program.md                   # Executor instructions (plays games via arc CLI)
research_program.md          # Researcher instructions (proposes strategies)
start_local_server.py        # Local game server (port 5050)
download_all_games.py        # Download all 25 games for offline use
generate_dashboard.py        # Static HTML dashboard generator
run_benchmark.py             # Programmatic benchmark runner
save_replay_frame.py         # Manual replay capture helper
environment_files/           # 25 downloaded games
experiments/
  log.md                     # Scorecard experiment log
  scorecards/                # Full scorecard JSON results
  replays/                   # Game replay data + frame PNGs
  play_strategy.md           # Current generic play strategy
  idea_queue.md              # Researcher's idea queue
  research_notes.md          # Researcher's journal
  breakthroughs.md           # Games where agent scored
src/arcagi3/
  cli/                       # arc CLI with scorecard support
  adapters/                  # LLM providers (MLX, Anthropic, OpenAI, ...)
  explorer_agent/            # LLM-per-step agent (legacy)
  stategraph_agent/          # Programmatic state-graph agent (legacy)
  adcr_agent/                # Reference ADCR agent
  agent.py                   # MultimodalAgent base class
  models.yml                 # Model configurations
```

## Links

- [ARC Prize](https://arcprize.org/) — The competition
- [ARC-AGI-3 Docs](https://docs.arcprize.org/) — Official documentation
- [ARC-AGI-3 Agents](https://github.com/arcprize/ARC-AGI-3-Agents) — Agent examples

## License

MIT
