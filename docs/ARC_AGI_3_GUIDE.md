# ARC-AGI-3: Complete Setup Guide for Autoresearch

> Everything you need to set up an agent repo and start running autoresearch against ARC-AGI-3 interactive reasoning games.
>
> **Competition launches:** March 25, 2026
> **Format:** Interactive game environments (NOT static grid puzzles)
> **Prize:** $1M grand prize (ARC-AGI-2 continues in parallel)
> **Website:** [arcprize.org](https://arcprize.org) | **Docs:** [docs.arcprize.org](https://docs.arcprize.org) | **Portal:** [three.arcprize.org](https://three.arcprize.org)

---

## Table of Contents

1. [What Is ARC-AGI-3?](#what-is-arc-agi-3)
2. [How It Works (Layman's Terms)](#how-it-works-laymans-terms)
3. [Quick Start: Running in 5 Minutes](#quick-start-running-in-5-minutes)
4. [The Three Repos](#the-three-repos)
5. [Core API Reference](#core-api-reference)
6. [Environment Structure](#environment-structure)
7. [Scoring System](#scoring-system)
8. [Agent Architecture Options](#agent-architecture-options)
9. [Building Your Own Agent](#building-your-own-agent)
10. [Benchmarking Harness (arcagi3)](#benchmarking-harness-arcagi3)
11. [Autoresearch Strategy](#autoresearch-strategy)
12. [Preview Competition Learnings](#preview-competition-learnings)
13. [Competition Rules](#competition-rules)
14. [Reference Links](#reference-links)

---

## What Is ARC-AGI-3?

ARC-AGI-3 is the **first interactive reasoning benchmark** — a radical departure from ARC-AGI-1/2's static "complete the grid pattern" puzzles. Instead of looking at input/output grid pairs, your agent plays **video-game-like environments** where it must:

- **Explore** — no instructions are given, you must discover the rules
- **Plan** — achieve multi-step goals across many actions
- **Remember** — manage state, conditional interactions, latent information
- **Adapt** — every environment is hand-crafted and novel (no memorization)

**Scale:** 1,000+ levels across 150+ environments. Every environment is human-solvable.

**Key metric:** Not "did you solve it?" but **"how many actions did it take?"** — action efficiency compared to a human baseline.

---

## How It Works (Layman's Terms)

Imagine you're dropped into a small video game you've never seen. There's a grid-based world with colored tiles. You can move up/down/left/right, click, perform actions, or reset. There are NO instructions. You have to figure out:

- What you control
- What the goal is
- How the world responds to your actions
- What the "win" condition looks like

Then you need to actually beat all the levels. The fewer actions you take, the higher your score.

**Concretely:** Your agent receives a 2D integer grid (the "frame") after every action. The grid is the game state — different integer values represent different tile types (walls, player, objects, etc.). Each game has different mechanics, different tile meanings, different goals.

The games are things like:
- Navigate a maze to reach a goal
- Manipulate objects in a specific pattern
- Solve logic puzzles through interaction
- Discover hidden rules through experimentation

Games typically have 3-5 levels of increasing difficulty. The grid is usually 64x64 but varies per game.

---

## Quick Start: Running in 5 Minutes

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager (recommended): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- An ARC-AGI-3 API key from [three.arcprize.org](https://three.arcprize.org)

### Option A: Toolkit Only (Simplest)

```bash
# Create a new project
mkdir arc-agent && cd arc-agent
uv init
uv add arc-agi

# Set your API key
echo 'ARC_API_KEY=your-key-here' > .env

# Create a minimal agent
cat > play.py << 'EOF'
import random
from arcengine import GameState
import arc_agi

arc = arc_agi.Arcade()
env = arc.make("ls20", render_mode="terminal")
if env is None:
    print("Failed to create environment")
    exit(1)

for step in range(100):
    action = random.choice(env.action_space)
    action_data = {}
    if action.is_complex():
        action_data = {"x": random.randint(0, 63), "y": random.randint(0, 63)}

    obs = env.step(action, data=action_data)
    if obs and obs.state == GameState.WIN:
        print(f"Game won at step {step}!")
        break
    elif obs and obs.state == GameState.GAME_OVER:
        env.reset()

scorecard = arc.get_scorecard()
if scorecard:
    print(f"Final Score: {scorecard.score}, Actions: {scorecard.total_actions}")
EOF

# Run it
uv run python play.py
```

### Option B: Starter Agents (More Features)

```bash
git clone https://github.com/arcprize/ARC-AGI-3-Agents.git
cd ARC-AGI-3-Agents
cp .env.example .env
# Edit .env and add your ARC_API_KEY

uv sync

# Run the random agent
uv run main.py --agent=random --game=ls20

# Run the reasoning agent (uses OpenAI — needs OPENAI_API_KEY in .env)
uv run main.py --agent=reasoningagent --game=ls20
```

### Option C: Benchmarking Harness (Most Powerful)

```bash
git clone https://github.com/arcprize/arc-agi-3-benchmarking.git
cd arc-agi-3-benchmarking
uv venv && uv sync
cp .env.example .env
# Edit .env with ARC_API_KEY + LLM provider keys

# Check environment
uv run python -m arcagi3.runner --check

# List available games
uv run python -m arcagi3.runner --list-games

# List available models
uv run python -m arcagi3.runner --list-models

# Run a benchmark
uv run python -m arcagi3.runner \
  --game_id ls20 \
  --config gpt-5-2-openrouter \
  --max_actions 50
```

---

## The Three Repos

### 1. `arcprize/ARC-AGI` — The Toolkit
**[github.com/arcprize/ARC-AGI](https://github.com/arcprize/ARC-AGI)**

The core Python library (`pip install arc-agi`). Provides:
- `Arcade` class — main entry point
- `EnvironmentWrapper` — game interaction interface
- `Scorecard` management
- Local execution (2000+ FPS), online API, or hybrid modes
- `listen_and_serve()` — Flask server for non-Python agents

**Key dependency:** `arcengine` (compiled game engine, installed automatically)

### 2. `arcprize/ARC-AGI-3-Agents` — Starter Agents
**[github.com/arcprize/ARC-AGI-3-Agents](https://github.com/arcprize/ARC-AGI-3-Agents)**

Reference agent implementations:
- `Random` — random actions (baseline)
- `ReasoningAgent` — OpenAI vision model with hypothesis tracking
- `LLM` / `FastLLM` / `GuidedLLM` / `ReasoningLLM` — various LLM approaches
- `MultiModalLLM` — multimodal with image understanding
- `LangGraphFunc` / `LangGraphThinking` — LangGraph-based agents
- `SmolCodingAgent` / `SmolVisionAgent` — HuggingFace smolagents
- `Playback` — replay recorded sessions

Also includes a `Swarm` class for running agents against multiple games.

### 3. `arcprize/arc-agi-3-benchmarking` — Benchmarking Harness
**[github.com/arcprize/arc-agi-3-benchmarking](https://github.com/arcprize/arc-agi-3-benchmarking)**

The most feature-rich option. Provides:
- Agent registry + CLI runner
- Multi-provider LLM support (OpenAI, Anthropic, Gemini, OpenRouter, DeepSeek, Fireworks, Groq, HuggingFace)
- Model config via YAML
- Checkpointing + resume
- Cost/token accounting
- Per-action recording + reasoning logs
- `SessionContext` with persistent datastore
- Prompt templating (Jinja2)

**This is the best starting point for serious autoresearch.**

---

## Core API Reference

### GameAction (the action space)

```python
from arcengine import GameAction

GameAction.RESET    # Reset the game / start new game
GameAction.ACTION1  # Move Up
GameAction.ACTION2  # Move Down
GameAction.ACTION3  # Move Left
GameAction.ACTION4  # Move Right
GameAction.ACTION5  # Perform Action (context-dependent)
GameAction.ACTION6  # Click (requires x, y coordinates, 0-63)
GameAction.ACTION7  # Undo

# Check if action needs coordinates
action.is_complex()  # True for ACTION6 (click)
action.is_simple()   # True for all others

# Get action from ID
GameAction.from_id(1)  # ACTION1
GameAction.from_name("ACTION3")  # ACTION3
```

### GameState

```python
from arcengine import GameState

GameState.NOT_PLAYED    # Game not started
GameState.IN_PROGRESS   # Game currently playing (technically NOT_FINISHED)
GameState.WIN           # All levels completed
GameState.GAME_OVER     # Failed, need reset
```

### FrameDataRaw (observation from environment)

After every `env.step()`, you get a `FrameDataRaw`:

```python
obs = env.step(action, data=action_data)

obs.game_id              # str: game identifier
obs.frame                # list[ndarray]: layered 2D grids (the visual state)
obs.state                # GameState: current game state
obs.levels_completed     # int: number of levels beaten
obs.win_levels           # int: total levels needed to win
obs.guid                 # str: server session GUID
obs.full_reset           # bool: whether this was a full game reset
obs.available_actions    # list[int]: action IDs available right now
obs.action_input         # ActionInput: the action that produced this frame
```

The `frame` is the key data — it's a list of 2D numpy arrays. The **last** array is typically the current visible state. Different integer values = different tile types. Grid size varies per game (commonly 64x64).

### Arcade Class (main entry point)

```python
import arc_agi
from arc_agi import OperationMode

# Default: downloads games from API, runs locally
arc = arc_agi.Arcade()

# Offline only (2000+ FPS, no API calls)
arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)

# Online only (API execution)
arc = arc_agi.Arcade(operation_mode=OperationMode.ONLINE)

# Competition mode (required for leaderboard)
arc = arc_agi.Arcade(operation_mode=OperationMode.COMPETITION)

# List available games
for env_info in arc.get_environments():
    print(f"{env_info.game_id}: {env_info.title} tags={env_info.tags}")

# Create an environment
env = arc.make("ls20")                              # No rendering (max FPS)
env = arc.make("ls20", render_mode="terminal")       # Terminal ASCII art
env = arc.make("ls20", render_mode="terminal-fast")  # Terminal, no FPS cap
env = arc.make("ls20", render_mode="human")          # Matplotlib window

# Scorecards
card_id = arc.create_scorecard(tags=["my-experiment"])
scorecard = arc.get_scorecard(card_id)
final = arc.close_scorecard(card_id)

# Environment interaction
obs = env.step(GameAction.RESET)     # Start game
obs = env.step(GameAction.ACTION1)   # Move up
obs = env.step(GameAction.ACTION6, data={"x": 32, "y": 32})  # Click

# Current state
env.observation_space   # Last FrameDataRaw
env.action_space        # List of available GameActions
env.info                # EnvironmentInfo
```

### Configuration via Environment Variables

```bash
ARC_API_KEY=your-key          # API auth
ARC_BASE_URL=https://three.arcprize.org  # API endpoint
OPERATION_MODE=normal         # normal|online|offline|competition
ENVIRONMENTS_DIR=environment_files  # Local game storage
RECORDINGS_DIR=recordings     # Game recording storage
```

---

## Environment Structure

Each game is defined by:

### metadata.json
```json
{
    "game_id": "ls20-016295f7",
    "title": "LS20",
    "tags": ["exploration", "navigation"],
    "baseline_actions": [4, 8, 16, 20, 24],
    "class_name": "Ls20"
}
```

- `game_id`: Unique identifier (4-char prefix + optional version hash)
- `baseline_actions`: Human performance per level (action count). This is what your agent is scored against.
- `tags`: Categories for the game

### Game Source (Python)
Each game is a Python class inheriting from `arcengine`. Downloaded automatically when using NORMAL mode. Stored in `environment_files/<game_id>/`.

### Recordings (JSONL)
Every game session is recorded as JSONL with timestamps, actions, frame data, and state transitions. Stored in `recordings/<scorecard_id>/`.

### Known Public Games (as of March 2026)
- `ls20` — Navigation/exploration with latent state and memory mechanics
- `ft09` — Logic/pattern completion game
- `vc33` — Visual/logical reasoning
- More games are available with API key registration
- Private/holdout games used for competition scoring

---

## Scoring System

### Per-Level Score
```
score = min(100, (baseline_actions / your_actions)^2 * 100)
```

- `baseline_actions` = human performance (from metadata.json)
- `your_actions` = how many actions your agent took
- Perfect score (100) = matching or beating human efficiency
- If human took 8 actions and you took 16: `(8/16)^2 * 100 = 25`

### Per-Game Score
Weighted average of level scores (later levels weighted higher).

### Scorecard Score
Average across all games played.

### Competition Tiebreaker
1. Total levels completed (more = better)
2. Total actions across all games (fewer = better)
3. Submission timestamp (earlier = better)

---

## Agent Architecture Options

### Approach 1: Direct Toolkit (Most Control)

Use `arc-agi` library directly. Full control over the game loop.

```python
import arc_agi
from arcengine import GameAction, GameState

arc = arc_agi.Arcade()
env = arc.make("ls20")

# Your agent logic here
obs = env.step(GameAction.RESET)
while obs.state != GameState.WIN:
    action = your_agent.decide(obs)
    obs = env.step(action)

scorecard = arc.close_scorecard()
```

### Approach 2: Agents Repo (Quick Prototyping)

Extend the `Agent` base class from the ARC-AGI-3-Agents repo.

```python
from arcengine import FrameData, GameAction, GameState
from agents.agent import Agent

class MyAgent(Agent):
    MAX_ACTIONS = 200

    def is_done(self, frames, latest_frame):
        return latest_frame.state == GameState.WIN

    def choose_action(self, frames, latest_frame):
        if latest_frame.state in [GameState.NOT_PLAYED, GameState.GAME_OVER]:
            return GameAction.RESET

        # Your logic: examine latest_frame.frame (the grid)
        # Decide which GameAction to take
        return your_decision
```

Run with: `uv run main.py --agent=myagent --game=ls20`

### Approach 3: Benchmarking Harness (Best for Autoresearch)

Extend `MultimodalAgent` from the benchmarking repo. You implement ONE method: `step()`.

```python
from arcagi3.agent import MultimodalAgent
from arcagi3.schemas import GameStep
from arcagi3.utils.context import SessionContext

class MyAgent(MultimodalAgent):
    def step(self, context: SessionContext) -> GameStep:
        # context.game — game state (score, available_actions, action_counter)
        # context.frames — current + previous frame grids
        # context.datastore — persistent key/value store (checkpointed!)
        # context.frame_images — PIL images of current frames
        # self.provider — LLM provider with cost tracking

        return GameStep(
            action={"action": "ACTION1"},
            reasoning={"why": "moving up to explore"},
        )
```

The harness gives you for free:
- **Checkpointing**: Resume where you left off after crashes
- **Cost tracking**: Per-action LLM token costs
- **SessionContext.datastore**: Persistent state that survives checkpoints
- **Provider abstraction**: Swap between OpenAI/Anthropic/Gemini/etc. via config
- **Recording**: Full action history with reasoning

Register and run:
```bash
uv run python -m arcagi3.runner \
  --agent my_agent \
  --game_id ls20 \
  --config claude-sonnet-4-5-20250929 \
  --max_actions 100
```

---

## Building Your Own Agent

### Step-by-Step (Benchmarking Harness)

#### 1. Create agent package

```
src/arcagi3/my_agent/
  __init__.py
  agent.py
  definition.py
  prompts/           # Optional Jinja2 templates
    system.prompt
```

#### 2. Implement the agent

```python
# src/arcagi3/my_agent/agent.py
from arcagi3.agent import MultimodalAgent
from arcagi3.schemas import GameStep
from arcagi3.utils.context import SessionContext

class MyAgent(MultimodalAgent):
    def step(self, context: SessionContext) -> GameStep:
        # Get current frame as grid
        grid = context.last_frame_grid  # 2D list of ints

        # Get game state
        score = context.game.current_score
        state = context.game.current_state
        actions_taken = context.game.action_counter
        available = context.game.available_actions

        # Access/update persistent memory
        memory = context.datastore.get("memory", "")
        hypotheses = context.datastore.get("hypotheses", [])

        # Call LLM via provider (with automatic cost tracking)
        messages = [
            {"role": "system", "content": "You are playing an unknown game..."},
            {"role": "user", "content": f"Grid:\n{grid}\nMemory:{memory}"},
        ]
        response = self.provider.call_with_tracking(
            context, messages, step_name="decide"
        )
        text = self.provider.extract_content(response)

        # Parse response into action
        action_name = parse_action(text)  # your parsing logic

        # Update memory
        context.datastore["memory"] = f"{memory}\nStep {actions_taken}: {action_name}"

        return GameStep(
            action={"action": action_name},
            reasoning={"raw_response": text[:200]},
        )
```

#### 3. Create the definition

```python
# src/arcagi3/my_agent/definition.py
from arcagi3.my_agent.agent import MyAgent

definition = {
    "name": "my_agent",
    "description": "My custom agent",
    "agent_class": MyAgent,
}
```

#### 4. Register in the runner

Add to `src/arcagi3/runner.py`:
```python
from arcagi3.my_agent.definition import definition as my_definition

def _build_default_registry() -> AgentRunner:
    runner = AgentRunner()
    runner.register(adcr_definition)
    runner.register(my_definition)  # Add this
    return runner
```

#### 5. Run it

```bash
uv run python -m arcagi3.runner \
  --agent my_agent \
  --game_id ls20 \
  --config claude-sonnet-4-5-20250929 \
  --max_actions 100
```

### Working with Frames (Vision)

Convert grid frames to images for multimodal LLMs:

```python
# In your agent's step():
from arcagi3.utils.image import grid_to_image

# Get current frame as PIL Image
image = context.last_frame_image(resize=(512, 512))

# Get previous frame for comparison
prev_images = context.previous_images

# Build vision message
import base64, io
buf = io.BytesIO()
image.save(buf, format="PNG")
b64 = base64.b64encode(buf.getvalue()).decode()

messages = [
    {"role": "user", "content": [
        {"type": "text", "text": "What should I do?"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
    ]}
]
```

### Working with Frames (Text)

For text-only agents:

```python
from arcagi3.utils.formatting import grid_to_text_matrix

grid = context.last_frame_grid
text = grid_to_text_matrix(grid)
# Returns a string representation of the 2D grid
```

### Using the Datastore (Agent Memory)

```python
# Store hypotheses
context.datastore["hypotheses"] = [
    {"name": "goal_is_reach_green", "confidence": 0.7},
    {"name": "clicking_toggles_state", "confidence": 0.3},
]

# Store action plan
context.datastore["plan"] = ["move right 3x", "click center", "observe"]

# Store scratchpad
context.datastore["memory_prompt"] = "Walls are black. Player is blue/orange. Door has pink border."

# Append to list (thread-safe)
context.datastore.append("action_log", {"step": 5, "action": "ACTION1", "result": "moved up"})

# All values MUST be JSON-serializable (for checkpointing)
```

---

## Benchmarking Harness (arcagi3)

### Model Configuration (YAML)

Models are configured in `src/arcagi3/models.yml`. Add your own in `models_private.yml`:

```yaml
models:
  - name: "claude-sonnet-4-5"
    model_name: "claude-sonnet-4-5-20250929"
    provider: "anthropic"
    is_multimodal: true
    max_tokens: 8192
    stream: true
    thinking:
      type: "enabled"
      budget_tokens: 4096
    pricing:
      date: "2025-09-29"
      input: 3.00
      output: 15.00

  - name: "my-local-model"
    model_name: "my-model"
    provider: "openai"  # OpenAI-compatible endpoint
    is_multimodal: false
    max_tokens: 4096
    pricing:
      date: "2026-03-20"
      input: 0.0
      output: 0.0
```

### CLI Options

```bash
uv run python -m arcagi3.runner \
  --agent AGENT_NAME \          # Agent to use
  --game_id GAME_ID \           # Game to play
  --config MODEL_CONFIG \       # Model config name
  --max_actions 200 \           # Max total actions
  --max_episode_actions 80 \    # Max actions per episode/reset
  --num_plays 3 \               # Number of attempts
  --use_vision \                # Enable vision (multimodal)
  --show_images \               # Display frames
  --checkpoint_frequency 10 \   # Save checkpoint every N actions
  --close_on_exit \             # Close scorecard on exit
  --retry_attempts 3 \          # Retries on LLM failure
  --save_results_dir results/   # Where to save results
```

### Checkpoints

```bash
# List checkpoints
uv run python -m arcagi3.runner --list-checkpoints

# Resume from checkpoint
uv run python -m arcagi3.runner --checkpoint CARD_ID

# Checkpoint files (in .checkpoint/<CARD_ID>/):
#   metadata.json        — game state, config, datastore snapshot
#   costs.json           — total usage and costs
#   action_history.json  — per-action results + reasoning
#   model_completion.json — full LLM prompts/responses
#   error.json           — error details (if failed)
```

---

## Autoresearch Strategy

### Why ARC-AGI-3 Is Perfect for Autoresearch

- **Scalar metric**: Action efficiency score (0-100 per level)
- **Fast local iteration**: OFFLINE mode at 2000+ FPS — no API latency
- **Machine-readable everything**: JSON metadata, JSONL recordings, programmatic scorecard API
- **Checkpointing**: Resume experiments after crashes
- **Multiple games**: Test generalization across different environments
- **Cost tracking**: Built-in LLM cost accounting

### Autoresearch Loop Design

```
┌─────────────────────────────────────────────────┐
│                 OUTER LOOP                       │
│  (Claude Code / autoresearch controller)         │
│                                                  │
│  1. Read current agent code + results            │
│  2. Analyze: what's working, what's not          │
│  3. Generate hypothesis for improvement          │
│  4. Modify agent code                            │
│  5. Run benchmark (inner loop)                   │
│  6. Compare results to baseline                  │
│  7. Accept/reject change                         │
│  8. Log result, update strategy                  │
│  9. Repeat                                       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│                 INNER LOOP                       │
│  (agent playing the game)                        │
│                                                  │
│  for each game:                                  │
│    1. Reset game                                 │
│    2. Observe frame                              │
│    3. Decide action                              │
│    4. Take action                                │
│    5. Check: WIN? GAME_OVER? Continue?           │
│    6. Update memory/hypotheses                   │
│  Return scorecard (levels, actions, score)        │
└─────────────────────────────────────────────────┘
```

### Practical Setup on Mac Studio

```bash
# Clone the benchmarking harness
git clone https://github.com/arcprize/arc-agi-3-benchmarking.git
cd arc-agi-3-benchmarking
uv venv && uv sync

# Set up .env
cat > .env << 'EOF'
ARC_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key
OPERATION_MODE=normal
EOF

# Verify setup
uv run python -m arcagi3.runner --check

# Create your agent
mkdir -p src/arcagi3/my_agent/prompts
# ... implement agent (see Building Your Own Agent above)

# Run a baseline
uv run python -m arcagi3.runner \
  --agent my_agent \
  --game_id ls20 \
  --config claude-sonnet-4-5-20250929 \
  --max_actions 100 \
  --save_results_dir results/baseline

# Iterate: modify agent, re-run, compare scores
```

### Experiment Tracking

The benchmarking harness already saves:
- `results/<config>/` — per-run results
- `.checkpoint/<card_id>/` — full state + action history
- Scorecards at `three.arcprize.org/scorecards`

For autoresearch, add:
- Git branch per experiment
- `experiment_log.jsonl` tracking: agent version, game, score, actions, cost
- Diff between baseline and experiment agent code

### Key Dimensions to Explore

1. **Exploration strategy**: Random vs. systematic vs. novelty-seeking
2. **State representation**: Raw grid vs. diff vs. abstracted features
3. **Memory design**: What to remember, how to compress, when to forget
4. **Hypothesis formation**: How to build and test theories about game mechanics
5. **Planning depth**: Reactive vs. look-ahead vs. goal decomposition
6. **Vision vs. text**: Multimodal LLM vs. grid-as-text
7. **Model selection**: Cost vs. capability tradeoff per-step
8. **Action budgeting**: When to explore vs. exploit discovered strategies

---

## Preview Competition Learnings

From the 30-day developer preview (July-August 2025, 12 submissions):

### What Worked

| Rank | Agent | Score | Approach |
|------|-------|-------|----------|
| 1st | StochasticGoose (Tufa Labs) | 12.58% | CNN-based RL predicting frame changes |
| 2nd | Blind Squirrel | 6.71% | State graph with ResNet18 value model |
| 3rd | Explore Till You Solve It | 3.64% | Frame graph exploration |
| HM | Fluxonian | 8.04% | DSL + LLM hybrid |

### Key Insights

1. **Smart exploration beats random**: StochasticGoose learned what was clickable after initial exploration. Blind Squirrel built state graphs and pruned loops.
2. **Pure LLMs struggled**: Approaches relying primarily on language models scored 3.7-4.4%. Vision helps but isn't sufficient alone.
3. **Random brute-force fails at scale**: One submission needed 278,158 actions where humans needed 300-600.
4. **Humans dramatically outperform AI**: Best agent achieved 12.58% of human efficiency. Humans excel at brief exploration → effective strategy execution.
5. **RL approaches led**: The top 2 submissions both used reinforcement learning (CNN + ResNet).
6. **Generalization is the hard part**: Solutions overfit to public games, struggled on private holdouts.

### Human Performance Patterns
- Average 300-600 actions per game
- Brief exploration phase, then efficient execution
- Consistently first-try completion
- 1,200+ players completed 3,900+ games in the preview

### Implications for Agent Design
- **Don't just use an LLM**: RL or hybrid approaches dominate
- **Learn from actions**: Track what causes frame changes vs. no-ops
- **Build state graphs**: Detect loops, prune useless actions
- **Separate exploration from exploitation**: Explore efficiently, then execute plans
- **Generalize**: Don't overfit to public games — design for novel environments

---

## Competition Rules

Based on the preview competition (final 2026 rules expected March 25):

- **Open source required**: All submissions must be open source for prize consideration
- **Compute limits**:
  - API-based: < $1K to reproduce on 5 games within 8 hours
  - Compute-based: Evaluated on RTX 5090, 8 hours
- **Anti-overfitting**: Public game scores + ARC Prize discretion for private testing
- **Team size**: Max 10 members
- **Reproducibility**: Must be easily reproducible with minimal effort
- **Tiebreaker**: Fewer actions → earlier submission

---

## Reference Links

### Official
- [ARC Prize](https://arcprize.org) — Main site
- [ARC-AGI-3 Overview](https://arcprize.org/arc-agi/3/) — What is ARC-AGI-3
- [ARC-AGI-3 Portal](https://three.arcprize.org) — API keys, scorecards, play games
- [ARC-AGI-3 Docs](https://docs.arcprize.org) — Technical documentation
- [ARC-AGI-3 Building Agents](https://three.arcprize.org/docs#building-agents) — Official agent-building guide
- [ARC-AGI-3 Preview Learnings](https://arcprize.org/blog/arc-agi-3-preview-30-day-learnings) — 30-day preview results

### Repos
- [arcprize/ARC-AGI](https://github.com/arcprize/ARC-AGI) — Toolkit (v0.9.5)
- [arcprize/ARC-AGI-3-Agents](https://github.com/arcprize/ARC-AGI-3-Agents) — Starter agents
- [arcprize/arc-agi-3-benchmarking](https://github.com/arcprize/arc-agi-3-benchmarking) — Benchmarking harness (v0.9.0)

### Papers
- [On the Measure of Intelligence](https://arxiv.org/abs/1911.01547) — Chollet's foundational paper (ARC basis)
- [ARC Prize 2025 Technical Report](https://arxiv.org/html/2601.10904) — Latest results and analysis

### Key Dependencies
- `arc-agi` (PyPI) — toolkit library, requires Python 3.12+
- `arcengine` (PyPI) — compiled game engine (installed as dependency)
- `arcagi3` (benchmarking repo) — requires Python 3.9+
- `uv` — recommended package manager

---

*Generated March 20, 2026 from direct inspection of all three repos at HEAD.*
