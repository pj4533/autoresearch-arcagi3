# Agent Guide

## How Agents Work

An agent is a Python class that decides what action to take at each step of an ARC-AGI-3 game. The benchmarking harness handles everything else: game communication, checkpointing, cost tracking, retries.

### The Contract

```python
class MyAgent(MultimodalAgent):
    def step(self, context: SessionContext) -> GameStep:
        # Examine context.frames, context.game, context.datastore
        # Optionally call LLM via self.provider
        # Return a GameStep with an action
        return GameStep(
            action={"action": "ACTION1"},
            reasoning={"why": "moving up to explore"}
        )
```

That's it. Everything else is optional.

## Available Actions

| Action | Name | Description |
|--------|------|-------------|
| ACTION1 | Move Up | Move the player/cursor up |
| ACTION2 | Move Down | Move the player/cursor down |
| ACTION3 | Move Left | Move the player/cursor left |
| ACTION4 | Move Right | Move the player/cursor right |
| ACTION5 | Perform Action | Context-dependent interaction |
| ACTION6 | Click | Click at x,y coordinates (0-127 range) |
| ACTION7 | Undo | Undo the last action |

Not all actions are available in every game. Check `context.game.available_actions` for the current game's action set (returns action numbers as strings, e.g., `("1", "2", "3", "4", "5")`).

## ADCR Agent (Reference)

Located in `src/arcagi3/adcr_agent/`. Four-step cognitive loop per action:

1. **Analyze** — Look at previous/current frames, describe what changed
2. **Decide** — Given analysis + memory, pick a human-readable action
3. **Convert** — Map the human action to a game ACTION
4. **Review** — Update memory scratchpad

Each step is a separate LLM call. This means 3 LLM calls per game action (analyze, decide, convert). Expensive but thorough.

Datastore keys used:
- `memory_prompt` — accumulated knowledge scratchpad
- `previous_prompt` — last prompt sent (for context)
- `previous_action` — last action taken
- `want_vision` — whether to send images (cached)

## Explorer Agent (Our Agent)

Located in `src/arcagi3/explorer_agent/`. Three-phase approach:

### Phase 1: Probe (no LLM calls)
- Systematically tries ACTION1-5 one at a time
- Records what changed in each frame after each action
- Builds an `action_effects` map: `{"ACTION1": "3 cells changed (2.1%)", ...}`
- Zero cost — pure programmatic exploration

### Phase 2: Explore (LLM-guided)
- Sends current frame + action effects map + hypotheses to Claude
- LLM analyzes the game state and picks the next action
- Updates hypotheses and memory after each action
- Two LLM calls per action (explore + convert)

### Phase 3: Exploit (planned, not yet implemented)
- When confident about the goal, execute plans without re-analyzing every frame
- Could be pure programmatic or reduced LLM usage

Datastore keys used:
- `phase` — current phase (`probe`, `explore`, `exploit`)
- `action_effects` — dict mapping actions to observed effects
- `hypotheses` — current best guess about game rules/goals
- `memory` — rolling log of observations
- `probe_index` — which probe action we're on
- `previous_action` — last action taken

## Creating a New Agent

### 1. Create the directory structure

```
src/arcagi3/myagent/
├── __init__.py
├── agent.py
├── definition.py
└── prompts/
    ├── system.prompt
    └── step.prompt      # whatever prompts you need
```

### 2. Implement the agent

```python
# agent.py
from arcagi3.agent import MultimodalAgent
from arcagi3.schemas import GameStep
from arcagi3.utils.context import SessionContext

class MyAgent(MultimodalAgent):
    def __init__(self, *args, use_vision=True, show_images=False,
                 memory_word_limit=None, **kwargs):
        super().__init__(*args, **kwargs)
        # your init here

    def step(self, context: SessionContext) -> GameStep:
        # Your logic here
        return GameStep(
            action={"action": "ACTION1"},
            reasoning={"agent": "myagent"}
        )
```

### 3. Create the definition

```python
# definition.py
from arcagi3.myagent import MyAgent

agents = [{"name": "myagent", "description": "My custom agent", "agent_class": MyAgent}]
```

### 4. Register it

In `src/arcagi3/runner.py`, add to `_build_default_registry()`:
```python
from arcagi3.myagent.definition import agents as myagent_definition
runner.register(myagent_definition)
```

And in `main.py`:
```python
from arcagi3.myagent.definition import agents as myagent_definition
runner.register(myagent_definition)
```

### 5. Run it

```bash
uv run python -m arcagi3.runner --agent myagent --game_id ls20 \
  --config claude-sonnet-4-5-20250929-thinking-8k --max_actions 40 --offline
```

## Using the LLM Provider

The agent has access to `self.provider` (a `ProviderAdapter` instance):

```python
# Build messages (OpenAI-style format, adapters handle conversion)
messages = [
    {"role": "system", "content": "You are a game agent."},
    {"role": "user", "content": [
        {"type": "text", "text": "What action should I take?"},
        # For images (when use_vision=True):
        make_image_block(image_to_base64(some_pil_image))
    ]}
]

# Call with automatic cost tracking
response = self.provider.call_with_tracking(context, messages, step_name="decide")

# Extract text from response
text = self.provider.extract_content(response)
```

Image helpers from `arcagi3.utils.image`:
- `grid_to_image(grid)` — convert frame grid to PIL Image
- `image_to_base64(img)` — convert PIL Image to base64 string
- `make_image_block(b64)` — create message content block for images
- `image_diff(img1, img2)` — create diff image highlighting changes

Text helper from `arcagi3.utils.formatting`:
- `grid_to_text_matrix(grid)` — convert frame grid to text representation

JSON extraction from `arcagi3.utils.parsing`:
- `extract_json_from_response(text)` — extract JSON dict from LLM output

## Tips

- **Cost matters**: Each LLM call costs money. The probe phase idea (trying actions without LLM) is about reducing cost while gathering useful information.
- **Action efficiency matters**: ARC-AGI-3 scores penalize using more actions than humans. Every action counts, including RESETs.
- **Use `context.datastore`**: It persists across steps and survives checkpoints (values must be JSON-serializable).
- **Frame grids**: Each frame is a 2D list of integers. Different integers = different colors/objects. Compare frames to detect changes.
- **Available actions vary**: Some games only have movement (1-4), others have all 7. Always check `context.game.available_actions`.
