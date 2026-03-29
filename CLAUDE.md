# ARC-AGI-3 Autoresearch

Autonomous research system for ARC-AGI-3 game-playing agents. Runs experiments overnight on local hardware (Mac Studio M2 Ultra) using Qwen models via MLX at zero API cost, with a two-agent loop that proposes and tests agent improvements automatically.

Also supports cloud API models (Anthropic, OpenAI, Gemini, etc.) for validation and comparison.

## Build & Run

```bash
# Install core dependencies
uv sync

# Install with MLX support (local models on Apple Silicon)
uv sync --extra mlx

# Install everything
uv sync --extra mlx

# Check environment (API keys, connectivity)
uv run python -m arcagi3.runner --check

# List available games
uv run python -m arcagi3.runner --list-games

# List registered agents
uv run python -m arcagi3.runner --list-agents

# List available model configs for enabled providers
uv run python -m arcagi3.runner --list-models
```

## Running Games

### With Cloud API Models
```bash
# Online (scores submitted to ARC server)
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 100 --save_results_dir results/explorer

# Offline (local only, no scorecard, fast iteration)
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 40 --offline
```

### With Local MLX Models (Apple Silicon)
```bash
# First run downloads model from HuggingFace (~20GB for primary model)
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config qwen3.5-35b-local \
  --max_actions 40 --offline
```

Offline mode skips scorecard creation/submission on the ARC server. Games run via the local `arcengine` library. A local `card_id` is generated for checkpointing.

### Resuming from Checkpoint
```bash
uv run python -m arcagi3.runner --list-checkpoints
uv run python -m arcagi3.runner --checkpoint <card_id>
```

## Autoresearch System

Two-agent flywheel: a **Researcher** proposes experiment ideas and a **Executor** implements and tests them. They run as separate Claude Code sessions, coordinating via markdown files in `experiments/`.

### Two-Agent Architecture

| Agent | Terminal | Reads | Writes |
|-------|---------|-------|--------|
| Executor | Terminal 2 | `experiments/idea_queue.md` | `experiments/log.md`, `experiments/breakthroughs.md`, agent code |
| Researcher | Terminal 3 | `experiments/log.md`, `experiments/breakthroughs.md`, agent code | `experiments/idea_queue.md`, `experiments/research_notes.md` |

- **`program.md`** — Executor instructions (read this to start the executor)
- **`research_program.md`** — Researcher instructions (read this to start the researcher)

### Git Model

All work happens on `main`. No branches.
- **Accept (score improved):** commit agent code + logs
- **Reject/neutral:** `git checkout -- src/arcagi3/explorer_agent/`, commit only logs

### Running a Benchmark

```bash
# Run all 3 games with default config
uv run python run_benchmark.py

# Quick screen with one game
uv run python run_benchmark.py --games ls20 --max-actions 40

# Custom config
uv run python run_benchmark.py --config qwen3.5-35b-local --max-actions 40
```

### Dashboard

Static HTML dashboard generated from `experiments/log.md`. No server dependencies.

```bash
# Generate dashboard
uv run python generate_dashboard.py

# Serve it (in a separate terminal)
cd experiments && python3 -m http.server 8080
# Open http://localhost:8080/dashboard.html
```

### Local Game Server

Run games locally instead of hitting the remote API:

```bash
# Start local server (runs on port 5000)
uv run python start_local_server.py
```

The `.env` file has `ARC_URL_BASE=http://localhost:5000` which routes all game requests to localhost.

### Overnight Run Pattern
```bash
# Terminal 1: Local game server
uv run python start_local_server.py

# Terminal 2: Dashboard server
cd experiments && python3 -m http.server 8080 --bind 0.0.0.0

# Terminal 3: Executor (Claude Code session)
claude
# "Read program.md and begin the autoresearch loop."

# Terminal 4: Researcher (Claude Code session)
claude
# "Read research_program.md and begin the research loop."
```

### Coordination Files

All in `experiments/` (tracked in git):
- `idea_queue.md` — Prioritized idea queue (researcher writes, executor pops)
- `log.md` — Master experiment log (executor writes, researcher reads)
- `breakthroughs.md` — Accepted improvements (executor writes)
- `research_notes.md` — Researcher's journal (researcher writes)

## ARC CLI (for Claude Code)

The `arc` CLI lets Claude Code play ARC-AGI-3 games directly via Bash. Two backends: local (default, 2000+ FPS, no API key needed for games) and API (official scoring via `three.arcprize.org`).

```bash
# List available games
arc list-games

# Start a game session (local backend)
arc start ls20 --max-actions 40

# Take actions
arc action move_up
arc action move_down
arc action move_left
arc action move_right
arc action perform
arc action click --x 32 --y 16
arc action undo

# View current state (--image saves PNG to .arc_session/frame.png)
arc state
arc state --image

# Show session metadata
arc info

# End session (prints summary, cleans up)
arc end
```

Session state persists in `.arc_session/session.json`. Only one session can be active at a time.

### Game-Specific Notes
- **ft09** — Pattern completion puzzle. Click blocks in the answer grid to toggle colors (9 to 8), then `perform` to submit. Multiple levels per game.
- **ls20** — Navigation/exploration with latent state. Directional moves shift elements on the grid. Has hidden state mechanics.
- **vc33** — Visual/logical reasoning.

## Architecture

### Core Framework
- `src/arcagi3/agent.py` — `MultimodalAgent` base class. Agents implement `step(context) -> GameStep`
- `src/arcagi3/runner.py` — CLI runner with agent registry
- `src/arcagi3/arc3tester.py` — Orchestration: scorecard, checkpoint, game loop
- `src/arcagi3/game_client.py` — ARC-AGI-3 API client
- `src/arcagi3/utils/context.py` — `SessionContext` passed to each step (frames, score, datastore)
- `src/arcagi3/prompts/manager.py` — Jinja2 template loader (discovers prompts relative to caller)

### LLM Adapters
- `src/arcagi3/adapters/` — Provider adapters implementing `ProviderAdapter` ABC
- Cloud: Anthropic, OpenAI, Gemini, DeepSeek, OpenRouter, Groq, Fireworks, xAI, Grok
- Local: **MLX** (Apple Silicon, zero cost) — runs Qwen models via `mlx-lm`
- `src/arcagi3/models.yml` — All model configurations with pricing

### Agents
- `src/arcagi3/adcr_agent/` — Reference ADCR agent (Analyze -> Decide -> Convert -> Review)
- `src/arcagi3/explorer_agent/` — Custom Probe -> Explore -> Exploit agent (LLM-per-step, original)
- `src/arcagi3/stategraph_agent/` — Programmatic state-graph explorer (primary research target). Builds directed graph of game states, systematically tries untried actions, calls LLM only every ~15 steps for hypothesis formation. Matches competition-winning approach.

### Autoresearch System
- `program.md` — Executor agent instructions (Claude Code reads this)
- `research_program.md` — Researcher agent instructions (Claude Code reads this)
- `run_benchmark.py` — Run all 3 games and print summary (executor calls this)
- `generate_dashboard.py` — Generate static HTML dashboard from `experiments/log.md`
- `src/arcagi3/autoresearch/experiment_db.py` — SQLite experiment tracker
- `src/arcagi3/autoresearch/runner.py` — Batch experiment runner
- `src/arcagi3/autoresearch/queue_cli.py` — Experiment queue CLI
- `src/arcagi3/autoresearch/mutations.py` — Mutation categories (7 categories)

### Creating a New Agent
1. Create `src/arcagi3/<name>_agent/` with `__init__.py`, `agent.py`, `definition.py`, `prompts/`
2. Agent class extends `MultimodalAgent`, implements `step(context: SessionContext) -> GameStep`
3. Uses `PromptManager` for Jinja2 templates in `prompts/` directory
4. `definition.py` exports `agents = [{"name": ..., "agent_class": ...}]`
5. Register in `src/arcagi3/runner.py` `_build_default_registry()` and `main.py`
6. Uses `context.datastore` (thread-safe dict) for persistent state between steps

### Game Actions
Available actions (from `agent.py` HUMAN_ACTIONS):
- ACTION1: Move Up
- ACTION2: Move Down
- ACTION3: Move Left
- ACTION4: Move Right
- ACTION5: Perform Action
- ACTION6: Click object (requires x,y coordinates 0-127)
- ACTION7: Undo

Not all actions are available in every game — check `context.game.available_actions`.

## Model Configs

### MLX Local (Apple Silicon, zero cost)
- `qwen3.5-35b-local` — Qwen3.5-35B MoE 4-bit (~60-70 tok/s, ~20GB RAM, primary)
- `qwen3-32b-local` — Qwen3-32B dense 4-bit (~20-30 tok/s, ~18GB, higher quality)
- `qwq-32b-local` — QwQ-32B reasoning 4-bit (~20-30 tok/s, ~18GB, chain-of-thought)
- `qwen3.5-27b-local` — Qwen3.5-27B 4-bit (~30+ tok/s, ~14GB, lightweight)

### Anthropic (Cloud API)
- `claude-sonnet-4-5-20250929-thinking-8k` — Sonnet 4.5 w/ 8k thinking (good default)
- `claude-sonnet-4-5-20250929-thinking-16k` — Sonnet 4.5 w/ 16k thinking
- `claude-sonnet-4-5-20250929-thinking-32k` — Sonnet 4.5 w/ 32k thinking budget
- `claude-sonnet-4-5-20250929` — Sonnet 4.5 no thinking
- `claude_haiku` — Haiku 3.5 (cheapest)
- `claude_opus` — Opus 3 (most capable)

See `models.yml` for the full list including OpenAI, Gemini, DeepSeek, Grok, and more.

## CLI Arguments Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--agent` | `adcr` | Agent name |
| `--game_id` | required | Game to play (e.g., `ls20`, `ft09`, `vc33`) |
| `--config` | required | Model config from `models.yml` |
| `--max_actions` | 40 | Max actions across all plays (0 = unlimited) |
| `--max_episode_actions` | 0 | Max actions per episode (0 = unlimited) |
| `--num_plays` | 0 | Number of plays (0 = infinite) |
| `--offline` | false | Skip scorecard submission |
| `--save_results_dir` | `results/<config>` | Where to save results JSON |
| `--checkpoint` | none | Resume from checkpoint card_id |
| `--checkpoint-frequency` | 1 | Save checkpoint every N actions |
| `--use_vision` | true | Send frames as images (vs text grids) |
| `--memory-limit` | 500 | Memory scratchpad word limit |
| `--verbose` | false | DEBUG logging for app code |
| `--show-images` | false | Display frames in terminal |

All flags can also be set via environment variables (e.g., `MAX_ACTIONS=100`).

## Autoresearch Strategy

### What We Iterate On
ARC-AGI-3 autoresearch iterates on **agent strategy**, not model weights:

| Dimension | What Changes | Example |
|-----------|-------------|---------|
| Prompts | System prompt, explore prompt, analysis templates | "Add explicit hypothesis-testing instructions" |
| Exploration heuristics | How the agent decides what to try | "Systematic grid scanning instead of random" |
| State representation | How the agent tracks what it's learned | "Build an action-effect transition table" |
| Phase transitions | When to shift from exploring to exploiting | "Switch to exploit after 3 consistent hypotheses" |
| Memory management | What the agent remembers across actions | "Track position history to detect loops" |
| Multi-level transfer | Using knowledge from level N for level N+1 | "Preserve action-effect map across levels" |

### Mutation Categories
The autoresearch system can modify agents across 7 categories: prompt engineering, exploration strategy, state tracking, phase transitions, memory management, preprocessing, and action sequencing. See `src/arcagi3/autoresearch/mutations.py` for details.

### Experiment Tracking
- Primary: `experiments/log.md` — markdown table with all experiment results
- Secondary: SQLite (`experiments/experiments.db`) — structured queries via `experiment_db.py`
- Verdicts: `improved` (score went up), `reverted` (score same or worse), `baseline` (reference run)

## Scoring

ARC-AGI-3 scores on action efficiency vs human baseline:
- Score = max(0, 1 - (agent_actions / (3 * human_actions)))
- Fewer actions = better score
- Every RESET counts as an action
- Games: 1000+ levels across 150+ environments

## Key Insights from Preview Competition

- Pure LLM approaches scored 3.7-4.4%
- RL/hybrid approaches dominated (12.58% top score)
- Strategy: start LLM-based, progressively add programmatic exploration
- Reduce LLM dependency for better action efficiency and lower cost

## Environment

- Python 3.12 via uv (`.python-version`)
- API keys in `.env`: `ARC_API_KEY`, `ANTHROPIC_API_KEY` (for cloud models)
- No API keys needed for local MLX models or offline game runs
- Results saved to `results/` (gitignored)
- Experiment DB at `experiments/experiments.db` (gitignored)
- Experiment log at `experiments/log.md` (tracked in git)
- Coordination files in `experiments/` (tracked in git)
- Checkpoints saved to `.checkpoint/` (gitignored)
- Available games (committed): `ls20`, `ft09`, `vc33`
