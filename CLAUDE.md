# ARC-AGI-3 Autoresearch

## Build & Run

```bash
# Install dependencies
uv sync

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

### Online (scores submitted to ARC server)
```bash
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 100 --save_results_dir results/explorer
```

### Offline (local only, no scorecard, fast iteration)
```bash
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 40 --offline
```

Offline mode skips scorecard creation/submission on the ARC server. Games still run via the local `arcengine` library. The agent still makes Anthropic API calls to decide actions — offline only means no ARC server communication. A local `card_id` is generated for checkpointing.

### Resuming from Checkpoint
```bash
# List available checkpoints
uv run python -m arcagi3.runner --list-checkpoints

# Resume a specific checkpoint
uv run python -m arcagi3.runner --checkpoint <card_id>
```

## Architecture

Built on `arc-agi-3-benchmarking` harness (copied in, not a submodule — we freely modify agent code).

### Core Framework
- `src/arcagi3/agent.py` — `MultimodalAgent` base class. Agents implement `step(context) -> GameStep`
- `src/arcagi3/runner.py` — CLI runner with agent registry
- `src/arcagi3/arc3tester.py` — Orchestration: scorecard, checkpoint, game loop
- `src/arcagi3/game_client.py` — ARC-AGI-3 API client
- `src/arcagi3/utils/context.py` — `SessionContext` passed to each step (frames, score, datastore)
- `src/arcagi3/adapters/` — LLM provider adapters (Anthropic, OpenAI, Gemini, etc.)
- `src/arcagi3/models.yml` — Model configurations with pricing
- `src/arcagi3/prompts/manager.py` — Jinja2 template loader (discovers prompts relative to caller)

### Agents
- `src/arcagi3/adcr_agent/` — Reference ADCR agent (Analyze->Decide->Convert->Review)
- `src/arcagi3/explorer_agent/` — Our custom Probe->Explore->Exploit agent

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

## Available Anthropic Model Configs

- `claude-sonnet-4-5-20250929-thinking-32k` — Sonnet 4.5 w/ 32k thinking budget
- `claude-sonnet-4-5-20250929-thinking-16k` — Sonnet 4.5 w/ 16k thinking
- `claude-sonnet-4-5-20250929-thinking-8k` — Sonnet 4.5 w/ 8k thinking (good default)
- `claude-sonnet-4-5-20250929-thinking-1k` — Sonnet 4.5 w/ 1k thinking (cheap)
- `claude-sonnet-4-5-20250929` — Sonnet 4.5 no thinking
- `claude-3-7-sonnet-20250219-thinking-16k` — Sonnet 3.7 w/ 16k thinking
- `claude-3-7-sonnet-20250219-thinking-8k` — Sonnet 3.7 w/ 8k thinking
- `claude-3-7-sonnet-20250219` — Sonnet 3.7 no thinking
- `claude_haiku` — Haiku 3.5 (cheapest, $0.80/$4.00 per 1M tokens)
- `claude_opus` — Opus 3 (most capable, $15/$75 per 1M tokens)

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

## Autoresearch Protocol

1. **Read** experiment log (`experiments/experiment_log.jsonl`)
2. **Hypothesize** — form a theory about what change will improve performance
3. **Modify** agent code (prompts, logic, phases)
4. **Run** benchmark: `uv run python -m arcagi3.runner --agent explorer --offline ...`
5. **Compare** results to baseline/previous best
6. **Log** result to experiment log
7. **Accept/Revert** — keep improvements, revert regressions

### Experiment Log Format
```json
{"experiment_id": "exp_001", "timestamp": "...", "agent": "explorer", "config": "...", "game_id": "ls20", "hypothesis": "...", "score": 0, "actions_taken": 45, "cost_usd": 0.12, "verdict": "pending"}
```

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
- API keys in `.env`: `ARC_API_KEY`, `ANTHROPIC_API_KEY` (required)
- Results saved to `results/` (gitignored)
- Experiments logged to `experiments/experiment_log.jsonl` (gitignored)
- Checkpoints saved to `.checkpoint/` (gitignored)
- Available games (as of setup): `ls20`, `ft09`, `vc33`
