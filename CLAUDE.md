# ARC-AGI-3 Autoresearch

Autonomous research system for ARC-AGI-3 game-playing agents. Runs experiments overnight on local hardware (Mac Studio M2 Ultra) using Qwen models via MLX at zero API cost, with a two-agent loop that proposes and tests agent improvements automatically.

Also supports cloud API models (Anthropic, OpenAI, Gemini, etc.) for validation and comparison.

## Build & Run

```bash
# Install core dependencies
uv sync

# Install with MLX support (local models on Apple Silicon)
uv sync --extra mlx

# Install with dashboard
uv sync --extra dashboard

# Install everything
uv sync --extra mlx --extra dashboard

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

The autoresearch system has three modes of operation:

### 1. Batch Experiment Runner
Queue experiments and run them sequentially. Good for overnight runs.

```bash
# Queue baseline experiments (4 configurations across all games)
uv run python -m arcagi3.autoresearch.runner --baselines

# Run all pending experiments
uv run python -m arcagi3.autoresearch.runner

# Run continuously until queue empty (for overnight)
uv run python -m arcagi3.autoresearch.runner --continuous

# Run a specific experiment
uv run python -m arcagi3.autoresearch.runner --experiment exp_005

# Retry failed experiments
uv run python -m arcagi3.autoresearch.runner --resume
```

### 2. Full Autoresearch Loop (Researcher + Executor)
Two-agent system: a researcher LLM proposes experiment ideas based on past results, and an executor implements the changes, runs the benchmark, and evaluates.

```bash
# Start autoresearch loop (runs until interrupted)
uv run python autoresearch.py --config qwen3.5-35b-local

# Run N experiments then stop
uv run python autoresearch.py --config qwen3.5-35b-local --max-experiments 5

# Research only (propose ideas, queue them, don't execute)
uv run python autoresearch.py --config qwen3.5-35b-local --research-only

# Execute only (run already-queued experiments)
uv run python autoresearch.py --config qwen3.5-35b-local --execute-only

# Start with baselines, then autoresearch
uv run python autoresearch.py --config qwen3.5-35b-local --baselines
```

### 3. Experiment Queue CLI
Manually manage the experiment queue.

```bash
# Add experiment to queue
uv run python -m arcagi3.autoresearch.queue add \
  --hypothesis "Adding loop detection reduces wasted actions" \
  --games ls20,ft09,vc33 --config qwen3.5-35b-local

# List experiments
uv run python -m arcagi3.autoresearch.queue list

# Show experiment details
uv run python -m arcagi3.autoresearch.queue show exp_005

# Show best experiments by score
uv run python -m arcagi3.autoresearch.queue best --top 10

# Summary stats
uv run python -m arcagi3.autoresearch.queue summary
```

### Dashboard
Web dashboard showing experiment results, score timelines, per-game analysis, and live progress.

```bash
uv run python -m arcagi3.dashboard.app --port 8050
# Open http://localhost:8050

# Accessible on network (e.g., from another machine)
uv run python -m arcagi3.dashboard.app --host 0.0.0.0 --port 8050
```

### Overnight Run Pattern
```bash
# Start dashboard in background
uv run python -m arcagi3.dashboard.app --port 8050 &

# Start autoresearch loop (will run until interrupted or queue empty)
nohup uv run python autoresearch.py --config qwen3.5-35b-local --baselines > autoresearch.log 2>&1 &

# Monitor progress
tail -f autoresearch.log
```

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
- `src/arcagi3/explorer_agent/` — Custom Probe -> Explore -> Exploit agent (primary research target)

### Autoresearch System
- `src/arcagi3/autoresearch/experiment_db.py` — SQLite experiment tracker
- `src/arcagi3/autoresearch/runner.py` — Batch experiment runner
- `src/arcagi3/autoresearch/queue_cli.py` — Experiment queue CLI
- `src/arcagi3/autoresearch/researcher.py` — LLM-driven idea generation from experiment history
- `src/arcagi3/autoresearch/executor.py` — Applies changes, runs benchmarks, evaluates verdicts
- `src/arcagi3/autoresearch/mutations.py` — Mutation categories (prompt engineering, exploration strategy, state tracking, phase transitions, memory management, preprocessing, action sequencing)
- `autoresearch.py` — Main orchestrator entry point (repo root)

### Dashboard
- `src/arcagi3/dashboard/app.py` — Dash (Plotly) web application
- `src/arcagi3/dashboard/layouts/` — Pages: overview, experiments, games, live monitor

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
- Experiments stored in SQLite (`experiments/experiments.db`)
- Each experiment tracks: hypothesis, changes, per-game scores, actions, cost, verdict, git commit, prompt hash
- Verdicts: `accept` (improved), `reject` (regressed), `baseline`, `neutral`, `partial`

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
- Experiments also logged to `experiments/experiment_log.jsonl` (gitignored)
- Checkpoints saved to `.checkpoint/` (gitignored)
- Available games (committed): `ls20`, `ft09`, `vc33`
