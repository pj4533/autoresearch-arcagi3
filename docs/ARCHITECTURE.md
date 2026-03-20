# Architecture

## Overview

This project is an autoresearch system for ARC-AGI-3, built on top of the `arc-agi-3-benchmarking` harness. The benchmarking harness was copied directly (not as a submodule) so we can freely modify agent code, register custom agents, and iterate quickly.

## System Layers

```
┌─────────────────────────────────────────────────┐
│  Claude Code (autoresearch orchestrator)         │
│  - Reads experiment results                      │
│  - Modifies agent code/prompts                   │
│  - Runs benchmarks                               │
│  - Analyzes and iterates                         │
└──────────────────────┬──────────────────────────┘
                       │ runs
┌──────────────────────▼──────────────────────────┐
│  Runner (arcagi3.runner)                         │
│  - CLI argument parsing                          │
│  - Agent registry                                │
│  - Dispatches to ARC3Tester                      │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  ARC3Tester (arcagi3.arc3tester)                 │
│  - Scorecard management (open/close)             │
│  - Checkpoint management                         │
│  - Creates agent instance                        │
│  - Calls agent.play_game()                       │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  MultimodalAgent (arcagi3.agent)                 │
│  - Base class for all agents                     │
│  - Game loop: reset → step → execute → repeat    │
│  - Manages plays, actions, checkpoints           │
│  - Calls self.step(context) each iteration       │
└──────────────────────┬──────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   ADCRAgent    ExplorerAgent   (your agent)
```

## Key Classes

### MultimodalAgent (`src/arcagi3/agent.py`)

Abstract base class. The game loop lives here:

1. `play_game(game_id)` — outer loop managing plays and global action budget
2. `_run_session_loop()` — inner loop: get frame → call `step()` → execute action → update state
3. `step(context) -> GameStep` — **abstract**, each agent implements this

The base class handles:
- Retries and error handling
- Action execution via `GameClient`
- Checkpoint save/restore
- Cost tracking via `SessionContext`

### SessionContext (`src/arcagi3/utils/context.py`)

Passed to every `step()` call. Contains:

- `context.frames` — current and previous frame grids (tuple of 2D lists)
- `context.game` — game progress (score, state, action counters, available actions)
- `context.datastore` — thread-safe dict for agent-specific persistent state
- `context.metrics` — cost and token usage tracking
- `context.history` — action and model call history
- `context.frame_images` — PIL images generated from frame grids
- `context.last_frame_image()` — convenience for the latest frame

Important properties:
- `context.game.current_score` — levels completed
- `context.game.current_state` — "IN_PROGRESS", "WIN", or "GAME_OVER"
- `context.game.action_counter` — total actions taken
- `context.game.available_actions` — tuple of available action numbers

### GameStep (`src/arcagi3/schemas.py`)

What `step()` returns:

```python
GameStep(
    action={"action": "ACTION1"},  # required: action name
    reasoning={"analysis": "..."}  # optional: sent to ARC API
)
```

For ACTION6 (click), include coordinates:
```python
GameStep(
    action={"action": "ACTION6", "x": 64, "y": 32},  # 0-127 range, halved before API
    reasoning={...}
)
```

### PromptManager (`src/arcagi3/prompts/manager.py`)

Loads Jinja2 templates relative to the calling module:

```python
# In src/arcagi3/explorer_agent/agent.py:
pm = PromptManager()
pm.render("explore", {"score": 5})  # loads ./prompts/explore.prompt
```

Templates support full Jinja2: `{{ var }}`, `{% if %}`, `{% for %}`, filters.

### Provider Adapters (`src/arcagi3/adapters/`)

Each LLM provider has an adapter extending `ProviderAdapter`:
- `call_with_tracking(context, messages)` — preferred entrypoint, tracks cost
- `extract_content(response)` — get text from response
- `extract_usage(response)` — get token counts

Model configs are in `src/arcagi3/models.yml`. Each config specifies: model name, provider, pricing, kwargs (thinking budget, max tokens, etc.).

## Data Flow

```
Game API → frame grids → SessionContext.update()
                              ↓
                     agent.step(context)
                              ↓
                     LLM call (via adapter)
                              ↓
                     GameStep returned
                              ↓
                     _execute_game_action()
                              ↓
                     Game API → new frame grids
                              ↓
                     loop until WIN/GAME_OVER/max_actions
```

## File Organization

```
src/arcagi3/
├── agent.py                 # MultimodalAgent base class
├── arc3tester.py            # Orchestration (scorecard + checkpoint + game loop)
├── runner.py                # CLI runner + agent registry
├── game_client.py           # ARC-AGI-3 API client
├── schemas.py               # Pydantic models (GameStep, GameResult, Cost, etc.)
├── types.py                 # Type aliases
├── models.yml               # Model configurations
├── adapters/
│   ├── provider.py          # ProviderAdapter base class
│   ├── anthropic.py         # Anthropic adapter
│   ├── open_ai.py           # OpenAI adapter
│   └── ...                  # Other providers
├── adcr_agent/              # Reference agent
│   ├── agent.py
│   ├── definition.py
│   └── prompts/
├── explorer_agent/          # Our custom agent
│   ├── agent.py
│   ├── definition.py
│   └── prompts/
├── prompts/
│   └── manager.py           # Jinja2 prompt loader
├── utils/
│   ├── context.py           # SessionContext
│   ├── cli.py               # CLI argument handling
│   ├── image.py             # Grid-to-image conversion
│   ├── formatting.py        # Grid-to-text conversion
│   ├── parsing.py           # JSON extraction from LLM responses
│   ├── metrics.py           # Metrics collection
│   └── ...
├── breakpoints/             # Debugging breakpoint system
└── checkpoint.py            # Checkpoint save/restore
```
