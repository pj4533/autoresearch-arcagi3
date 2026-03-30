# ARC-AGI-3 Autoresearch

Autonomous research system for ARC-AGI-3 games. Claude Code (Opus 4.6) plays all 25 games directly via the `arc` CLI with vision, using a two-agent autoresearch loop to iteratively improve play strategy. Scores are tracked via scorecards directly comparable to the competition leaderboard.

**Every game is solvable by humans. This is a test for AI.**

## Quick Start

```bash
# Install dependencies
uv sync --extra mlx

# Download all 25 games (one-time)
uv run python download_all_games.py

# Start local game server
uv run python start_local_server.py

# Play a game interactively
uv run arc start vc33-9851e02b --max-actions 40
uv run arc state --image
uv run arc action click --x 32 --y 16
uv run arc end
```

## Scoring

```
Per-level: min(100, (baseline_actions / your_actions)² × 100)
Per-game: Weighted average of level scores (weight = level number; later levels count more)
Overall: Simple average across all 25 games in a scorecard
```

Match human baseline = 100%. Use 2x actions = 25%. Use 3x = 11%. Quadratic penalty — action efficiency is everything.

## 25 Games

```
ar25  bp35  cd82  cn04  dc22  ft09  g50t  ka59  lf52  lp85
ls20  m0r0  r11l  re86  s5i5  sb26  sc25  sk48  sp80  su15
tn36  tr87  tu93  vc33  wa30
```

All downloaded locally via `download_all_games.py`. Each has 6-10 levels, 181 total levels across all games. All solvable by humans.

## Autoresearch System

Two Claude Code sessions coordinate via markdown files:

| Agent | Role | Reads | Writes |
|-------|------|-------|--------|
| **Executor** | Plays games via `arc` CLI with vision | `idea_queue.md`, `play_strategy.md` | `log.md`, `breakthroughs.md`, `play_strategy.md` |
| **Researcher** | Proposes generic play strategies | `log.md`, `breakthroughs.md`, `play_strategy.md` | `idea_queue.md`, `research_notes.md` |

- **`program.md`** — Executor instructions
- **`research_program.md`** — Researcher instructions
- **`experiments/play_strategy.md`** — Generic play strategy (iterated on by both agents)

### Scorecard-Based Experiments

Each experiment = one full scorecard across all 25 games. The aggregate score is directly comparable to the ARC-AGI-3 competition leaderboard.

```bash
# Open scorecard (starts game 1 of 25)
uv run arc scorecard open --max-actions 40

# Play the game, then advance to next
uv run arc scorecard next

# Check progress anytime
uv run arc scorecard status

# Close scorecard (computes final aggregate score)
uv run arc scorecard close
```

Scorecard results saved to `experiments/scorecards/`. Dashboard updated automatically.

### Dashboard

Static HTML dashboard with three tabs: Progress (score history + 25-game heatmap), Scorecard Detail (per-game breakdown), Replays (frame-by-frame visual replay).

```bash
uv run python generate_dashboard.py
cd experiments && python3 -m http.server 8080 --bind 0.0.0.0
# Open http://localhost:8080/dashboard.html
```

### Replay System

Games are automatically recorded for visual replay. Frame PNGs captured on every action, replay JSONL generated on `arc end`. Viewable in the dashboard Replays tab.

### Running the System (4 terminals)

```bash
# Terminal 1: Local game server (serves all 25 games)
uv run python start_local_server.py

# Terminal 2: Dashboard
cd experiments && python3 -m http.server 8080 --bind 0.0.0.0

# Terminal 3: Executor (plays games via arc CLI)
claude
# /loop 10m Read program.md. Open scorecard, play all 25 games via arc CLI. NEVER modify Python code.

# Terminal 4: Researcher (proposes generic strategies)
claude
# /loop 10m Read research_program.md. Propose generic play strategies, NOT code changes.
```

## ARC CLI

```bash
# List games
uv run arc list-games

# Single game session
uv run arc start GAME_ID --max-actions 40
uv run arc state --image          # view frame (saves PNG)
uv run arc action move_up         # movement
uv run arc action click --x 32 --y 16  # click (0-127 coords)
uv run arc action perform         # perform action
uv run arc action undo            # undo
uv run arc end                    # end session

# Scorecard session (all 25 games)
uv run arc scorecard open --max-actions 40
uv run arc scorecard next         # advance to next game
uv run arc scorecard status       # check progress
uv run arc scorecard close        # finalize and score
```

## Architecture

### Core Framework
- `src/arcagi3/agent.py` — `MultimodalAgent` base class
- `src/arcagi3/runner.py` — CLI runner with agent registry
- `src/arcagi3/arc3tester.py` — Orchestration: scorecard, checkpoint, game loop
- `src/arcagi3/game_client.py` — ARC-AGI-3 API client
- `src/arcagi3/cli/` — `arc` CLI with scorecard support

### Agents (for programmatic benchmarks)
- `src/arcagi3/adcr_agent/` — ADCR agent (Analyze -> Decide -> Convert -> Review)
- `src/arcagi3/explorer_agent/` — Probe -> Explore -> Exploit agent
- `src/arcagi3/stategraph_agent/` — Programmatic state-graph explorer

### Autoresearch
- `program.md` — Executor instructions (Claude Code plays games directly)
- `research_program.md` — Researcher instructions (proposes generic strategies)
- `generate_dashboard.py` — Static HTML dashboard with replays
- `download_all_games.py` — Download all 25 games for offline use
- `save_replay_frame.py` — Manual replay capture (auto-capture built into CLI)
- `start_local_server.py` — Local game server on port 5050

### Game Actions
- ACTION1-4: Move Up/Down/Left/Right
- ACTION5: Perform Action
- ACTION6: Click (x,y coordinates 0-127)
- ACTION7: Undo

Not all actions available in every game.

## Environment

- Python 3.12 via uv
- Mac Studio M2 Ultra, 64GB RAM
- All games run locally via `start_local_server.py` (port 5050)
- `.env`: `ARC_API_KEY` + `ARC_URL_BASE=http://localhost:5050`
- No cloud API keys needed — Claude Code provides the reasoning
- Experiment log: `experiments/log.md`
- Scorecard results: `experiments/scorecards/`
- Replays: `experiments/replays/`
