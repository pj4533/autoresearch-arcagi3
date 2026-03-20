# Running Guide

## Prerequisites

- Python 3.12 (managed by uv via `.python-version`)
- uv package manager
- API keys in `.env`:
  - `ARC_API_KEY` — from [three.arcprize.org](https://three.arcprize.org)
  - `ANTHROPIC_API_KEY` — from [console.anthropic.com](https://console.anthropic.com)

## Setup

```bash
# Install all dependencies
uv sync

# Verify everything is configured
uv run python -m arcagi3.runner --check
```

The `--check` command tests API connectivity and shows which providers are available.

## Running Modes

### Online Mode (default)

Submits results to the ARC server via scorecards. Use this for official scoring.

```bash
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 100
```

This will:
1. Open a scorecard on the ARC server
2. Play the game, submitting each action
3. Close the scorecard when done
4. Save checkpoints to `.checkpoint/`

### Offline Mode

No scorecard submission. Games still run via the local `arcengine` library. Best for development and iteration.

```bash
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 40 --offline
```

This will:
1. Generate a local card ID (`local-<uuid>`)
2. Play the game locally
3. Save checkpoints locally
4. NOT submit anything to ARC server

**Important**: Offline mode still makes Anthropic API calls for the agent's LLM decisions. It only skips the ARC scorecard server communication.

### Via Environment Variables

All CLI flags can be set as environment variables:

```bash
export AGENT=explorer
export GAME_ID=ls20
export CONFIG=claude-sonnet-4-5-20250929-thinking-8k
export MAX_ACTIONS=40
export OFFLINE=true

uv run python -m arcagi3.runner
```

## Checkpoints

### How They Work

The system automatically checkpoints after every action (configurable with `--checkpoint-frequency`). Checkpoints save:
- Full game state (frames, score, counters)
- Agent's datastore contents
- Action history and model call history
- Cost tracking

Checkpoints are stored in `.checkpoint/<card_id>/`.

### Resuming

```bash
# See available checkpoints
uv run python -m arcagi3.runner --list-checkpoints

# Resume from a specific checkpoint
uv run python -m arcagi3.runner --checkpoint <card_id>
```

When resuming:
- Config and game_id are loaded from the checkpoint
- The agent continues from where it left off
- The datastore is fully restored

### Interrupting

You can safely Ctrl-C during a run. The last checkpoint will be preserved and you can resume later.

## Saving Results

Results are saved as JSON files when you specify `--save_results_dir`:

```bash
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 40 --offline \
  --save_results_dir results/my_experiment
```

Result files are named `{game_id}_{config}_{timestamp}.json` and contain:
- Final score and state
- Actions taken
- Duration
- Total cost
- Full action history

## Available Games

As of project setup, three games are available via the API:

| Game ID | Description |
|---------|-------------|
| `ls20` | LS20 |
| `ft09` | FT09 |
| `vc33` | VC33 |

Run `uv run python -m arcagi3.runner --list-games` for the current list (more games launch March 25).

## Useful Commands

```bash
# Check environment
uv run python -m arcagi3.runner --check

# List games
uv run python -m arcagi3.runner --list-games

# List games as JSON
uv run python -m arcagi3.runner --list-games --json

# List agents
uv run python -m arcagi3.runner --list-agents

# List available model configs
uv run python -m arcagi3.runner --list-models

# List checkpoints
uv run python -m arcagi3.runner --list-checkpoints

# Close a scorecard
uv run python -m arcagi3.runner --close-scorecard <card_id>

# Verbose logging
uv run python -m arcagi3.runner --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k --verbose --offline

# Text-only mode (no vision, cheaper)
uv run python -m arcagi3.runner --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k --no-use_vision --offline
```

## Troubleshooting

### "ARC_API_KEY not configured"
Add your key to `.env`: `ARC_API_KEY=your_key_here`

### "ANTHROPIC_API_KEY not found"
Add your key to `.env`: `ANTHROPIC_API_KEY=your_key_here`

### "Unknown agent"
Check registered agents with `--list-agents`. Make sure the agent is registered in both `runner.py` and `main.py`.

### "No games available"
The ARC API may be down, or your `ARC_API_KEY` may be invalid. Run `--check` to diagnose.

### Checkpoint resume fails
The scorecard may have expired on the server. Use `--offline` for local-only runs that don't depend on server state.
