# Autoresearch Protocol

## What Is Autoresearch?

Autoresearch is a loop where Claude Code drives iteration on the agent: modify code, run benchmarks, analyze results, repeat. The goal is to systematically improve agent performance on ARC-AGI-3 games.

## The Loop

```
┌──────────────────────────────────────────┐
│  1. Read experiment log                   │
│     - What's been tried?                  │
│     - What's the current best?            │
├──────────────────────────────────────────┤
│  2. Hypothesize                           │
│     - What might improve performance?     │
│     - What's the expected effect?         │
├──────────────────────────────────────────┤
│  3. Modify                                │
│     - Change agent code or prompts        │
│     - Keep changes small and testable     │
├──────────────────────────────────────────┤
│  4. Run                                   │
│     uv run python -m arcagi3.runner \     │
│       --agent explorer --game_id ls20 \   │
│       --config <model> --offline \        │
│       --max_actions 40                    │
├──────────────────────────────────────────┤
│  5. Compare                               │
│     - Score vs baseline/previous best     │
│     - Actions taken                       │
│     - Cost                                │
├──────────────────────────────────────────┤
│  6. Log                                   │
│     - Append to experiment_log.jsonl      │
├──────────────────────────────────────────┤
│  7. Accept or Revert                      │
│     - Keep improvements, revert failures  │
│     - git commit if accepting             │
└──────────────┬───────────────────────────┘
               │
               └──→ back to step 1
```

## Experiment Log

Location: `experiments/experiment_log.jsonl`

Each line is a JSON object:

```json
{
  "experiment_id": "exp_001",
  "timestamp": "2026-03-20T15:30:00Z",
  "agent": "explorer",
  "config": "claude-sonnet-4-5-20250929-thinking-8k",
  "game_id": "ls20",
  "hypothesis": "Probe phase builds action map cheaply before using LLM",
  "changes": "Initial explorer agent with 5-action probe phase",
  "score": 0,
  "actions_taken": 45,
  "cost_usd": 0.12,
  "verdict": "baseline",
  "notes": "First run, establishing baseline for explorer agent"
}
```

Fields:
- `experiment_id` — sequential ID (exp_001, exp_002, ...)
- `timestamp` — ISO 8601
- `agent` — agent name used
- `config` — model config used
- `game_id` — which game was tested
- `hypothesis` — what we expected to happen
- `changes` — what was modified
- `score` — final score (levels completed)
- `actions_taken` — total actions used
- `cost_usd` — total LLM cost
- `verdict` — `baseline`, `accept`, `reject`, `partial`
- `notes` — free-form observations

## Running Experiments

### Quick test (low cost)
```bash
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-1k \
  --max_actions 20 --offline
```

### Standard run
```bash
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 40 --offline
```

### Full evaluation (all games)
```bash
for game in ls20 ft09 vc33; do
  uv run python -m arcagi3.runner \
    --agent explorer --game_id $game \
    --config claude-sonnet-4-5-20250929-thinking-8k \
    --max_actions 100 --offline \
    --save_results_dir results/explorer
done
```

### Comparing agents
```bash
# Run ADCR baseline
uv run python -m arcagi3.runner \
  --agent adcr --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 100 --offline \
  --save_results_dir results/baseline

# Run explorer
uv run python -m arcagi3.runner \
  --agent explorer --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k \
  --max_actions 100 --offline \
  --save_results_dir results/explorer
```

Results are saved as JSON in the `--save_results_dir`.

## Scoring

ARC-AGI-3 scores on action efficiency vs human baseline:

```
score = max(0, 1 - (agent_actions / (3 × human_actions)))
```

- **Fewer actions = better score**
- Every RESET counts as an action
- Score of 1.0 = solved in 0 actions (impossible, but theoretical max)
- Score of 0.0 = used 3x or more the human baseline actions
- Negative scores are clamped to 0

### What this means for strategy
- Wasting actions on exploration costs score
- Every LLM call that leads to a wrong action is doubly expensive (cost + score penalty)
- The probe phase (trying actions without LLM) is free from cost but still uses actions
- An ideal agent would solve levels in fewer steps than 3x the human baseline

## Strategy Evolution

### Phase 1: LLM-based (current)
- Start with the Explorer agent's probe-explore-exploit approach
- Establish baselines on all three games
- Identify which games respond to which strategies

### Phase 2: Hybrid
- Add programmatic state analysis (frame differencing, object detection)
- Use LLM only for high-level planning, not every action
- Implement loop detection (avoid repeating failed sequences)

### Phase 3: Programmatic-first
- Build state graphs from exploration
- Use pathfinding for known game types
- LLM only for novel situations or hypothesis generation

## Key Insight

From the preview competition: pure LLM approaches scored 3.7-4.4%, while RL/hybrid approaches reached 12.58%. The path to better scores is reducing LLM dependency, not using a bigger model.
