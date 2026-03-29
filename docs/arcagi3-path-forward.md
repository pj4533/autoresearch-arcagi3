# ARC-AGI-3 Autoresearch: Findings & Path to First Score

**Prepared by Drift** — Independent code audit and analysis of `/host/developer/autoresearch-arcagi3`

---

## Executive Summary

After 18 experiments scoring 0.0000 across all three games, the autoresearch infrastructure works (two-agent loop, queue management, git commits, dashboards) but the agent cannot score because of a fundamental architecture mismatch: **you're running a text-only small local model against games that were designed to defeat LLMs**. The top three competition finishers all used programmatic approaches. Every LLM-only approach scored below 1%.

The path to first score is not another prompt tweak. It's an architectural shift: **replace the LLM-per-step loop with a programmatic exploration core that uses the LLM rarely, only for high-level reasoning.**

---

## What I Found (Code Audit)

### 1. The Click Coordinate Chain Works Correctly

I traced ACTION6 through all 8 layers from agent output to game engine. The chain:

```
Agent outputs x,y (0-127) → agent.py //2 → 0-63 display space
  → GameClient HTTP POST → Remote server (three.arcprize.org)
  → ComplexAction validates 0-63 → ActionInput.data
  → Game.step() → camera.display_to_grid(x, y) → grid coordinates
```

**The `//2` division is correct.** For VC33 level 1 (32x32 grid at 2x scale, no padding), sending `col*2` in 0-127 space produces the correct grid coordinate after `//2` then `/2`.

**Why brute-force clicks (exp 013) still produced zero frame changes:**

The BFS object detection finds ALL non-background cells in the 64x64 text frame — this includes walls, borders, and structural sprites. In VC33, only sprites tagged `"ZGd"` (sliders) and `"zHk"` (swappable elements) respond to clicks. Everything else is silently ignored. The brute-force was clicking structural elements (color 0, 4, 5) not interactive ones (likely colors 7, 9, 11 for small colorful objects).

Additionally, every ACTION6 **decrements the move counter** in VC33 regardless of whether it hits anything. Waste 50 clicks on non-interactive cells and the game ends in GAME_OVER.

### 2. All Experiments Hit the Remote API

Your `.env` has no `ARC_URL_BASE`. The `GameClient` defaults to `https://three.arcprize.org`. Even in "offline mode" (`submit_scorecard=False`), all game actions are sent to the remote server. The local arcengine installation is unused by the benchmark runner — it's only used by the `arc` CLI in local backend mode.

**Implication:** You're paying network latency on every action and you can't add debug logging to the game engine. For faster iteration, you should start a local game server.

### 3. `use_vision=False` Is Set for All Experiments

`runner.py:109`: `use_vision=False  # MLX models are text-only`

The agent receives 64x64 grids as JSON arrays — 8,000+ tokens per frame, zero spatial structure. For click-based games, the agent literally cannot "see" which elements are interactive. This is like playing a point-and-click adventure game with a screen reader that reads pixel RGB values.

The research notes cite a finding that visual input produced 0.0% → 97.1% improvement in one study. Vision is not a nice-to-have — for click games, it's load-bearing.

### 4. Explorer Agent Convert Prompt Doesn't Specify Coordinate Range

The ADCR agent's `find_action_instruct.prompt` says:
> "For ACTION6 (click), provide x and y coordinates (0-127 range, which will be divided by 2)"

The Explorer agent's `convert.prompt` says:
> "Only provide x and y if the action is ACTION6 (click). Otherwise omit them or set to 0."

No range specified. The LLM guesses, producing unpredictable coordinates.

### 5. The Competition Already Answered "How to Score"

From the research notes' own competition analysis:

| Approach | Score | Method |
|----------|-------|--------|
| 1st StochasticGoose | 12.58% | CNN + RL on frame-change signal |
| 2nd Blind Squirrel | 6.71% | Directed state graphs + value-ranked actions |
| 3rd Graph-based | solved 12 levels | Pure programmatic exploration, zero learning |
| Best LLM (Tomas) | 3.70% | Crashed often |
| Current frontier LLMs | <1% | Worse than random |

**Pure LLM approaches don't work here.** The 3rd place entry used ZERO machine learning — just state graphs, loop detection, and systematic exploration — and beat every LLM approach.

---

## Root Cause Analysis: Why 18 Experiments at 0 Score

The autoresearch has been optimizing the wrong layer. Here's what happened:

1. **Exps 001-005**: Thinking mode corrupted JSON → all actions defaulted to Move Up → 0
2. **Exp 006**: Disabled thinking → JSON parse fixed (72-100%) → **breakthrough**
3. **Exps 007-018**: Various prompt/memory/strategy improvements → click rates improved, speed improved, action diversity improved → still 0

The problem after exp 006 is NOT prompts, memory, or strategy. It's that:

- **VC33**: The agent clicks random cells. Only ~5-10 sprites out of ~4000 cells are clickable. Random clicking = ~0.2% chance per click. With 40 actions and 5 wasted on probing, you get ~35 clicks × 0.2% = ~7% chance of hitting ONE clickable sprite. And you need 6 CORRECT clicks in sequence.
- **FT09**: Same problem. 3x3 toggle pattern requires understanding constraint satisfaction — something a 35B model in text-only mode fundamentally cannot do.
- **LS20**: Navigation with hidden state. The agent loops between the same states. Without a state graph, it can't detect loops or plan paths.

Every experiment from 007-018 was a variation of "make the LLM do better in a task LLMs can't do." The autoresearch correctly identified the right ideas (state graph, click filtering, programmatic exploration) but didn't implement them deeply enough — it kept adding more prompting on top.

---

## The Path Forward

### Priority 1: Run a Local Game Server

**Why:** Removes network latency, enables debug logging in the game engine, makes experiments 2-5x faster, and lets you verify click handling.

**How:**
```python
# In run_benchmark.py or a new local_server.py
from arc_agi import Arcade
from arc_agi.server import create_app

arcade = Arcade(environment_dir="environment_files")
app, api = create_app(arcade)
app.run(host="0.0.0.0", port=5000)
```

Then set `ARC_URL_BASE=http://localhost:5000` in `.env`.

**Quick test after setup:**
```bash
# Verify clicking works at all
curl -X POST http://localhost:5000/api/cmd/RESET \
  -H "Content-Type: application/json" \
  -d '{"game_id": "vc33-9851e02b"}'
# Note the guid from response, then:
curl -X POST http://localhost:5000/api/cmd/ACTION6 \
  -H "Content-Type: application/json" \
  -d '{"game_id": "vc33-9851e02b", "guid": "<guid>", "x": 32, "y": 14}'
# Compare frame before and after
```

### Priority 2: Build a Programmatic Exploration Core

Stop calling the LLM every step. Build the 3rd-place architecture:

```python
class ProgrammaticExplorer:
    """
    Replaces LLM-per-step with systematic programmatic exploration.
    LLM called only for hypothesis formation (every ~10-20 actions).
    """

    def __init__(self):
        self.state_graph = {}  # hash(frame) → {action → hash(next_frame)}
        self.visited_states = set()
        self.action_queue = []
        self.click_targets = []  # Identified interactive elements

    def step(self, context):
        # 1. Hash current frame (mask status bar: top 2 + bottom 2 rows)
        frame_hash = self._hash_frame(context.frame_grids[-1])

        # 2. Record transition from previous state
        if self.prev_state and self.prev_action:
            self.state_graph.setdefault(self.prev_state, {})[self.prev_action] = frame_hash

        # 3. If score increased, record which action caused it
        if context.game.current_score > self.prev_score:
            self.winning_actions.append(self.prev_action)

        # 4. Choose next action (programmatic, no LLM)
        action = self._choose_action(frame_hash, context)

        self.prev_state = frame_hash
        self.prev_action = action
        return action

    def _choose_action(self, state_hash, context):
        # Priority 1: Try untried actions in this state
        tried = set(self.state_graph.get(state_hash, {}).keys())
        available = context.game.available_actions
        untried = [a for a in available if a not in tried]
        if untried:
            return untried[0]

        # Priority 2: Go to least-visited neighbor state
        neighbors = self.state_graph.get(state_hash, {})
        least_visited = min(neighbors.items(),
                          key=lambda x: self.visit_count.get(x[1], 0))
        return least_visited[0]

    def _hash_frame(self, grid):
        """Hash frame with status bar masked."""
        masked = grid[2:-2]  # Skip top/bottom 2 rows
        return hashlib.md5(str(masked).encode()).hexdigest()[:16]
```

**Why this works:** It systematically tries every action in every state, never loops, and builds a complete map. For LS20, this would find the navigation path. The LLM is only called occasionally to interpret high-level strategy.

### Priority 3: Smart Click Target Detection for VC33

The brute-force approach (exp 013) failed because it clicked non-interactive cells. Build a smarter detector:

```python
def detect_interactive_cells(grid, prev_grid=None):
    """
    Identify likely interactive cells by filtering out structural elements.

    Strategy:
    1. Find the background color (most common)
    2. Find border/structural colors (large connected regions)
    3. Remaining small colorful objects are likely interactive
    """
    flat = [c for row in grid for c in row]
    color_counts = Counter(flat)
    background = color_counts.most_common(1)[0][0]

    # BFS to find connected components
    components = bfs_connected_components(grid, exclude=[background])

    # Filter: interactive objects are SMALL and COLORFUL
    # Structural elements are LARGE (borders, walls, backgrounds)
    interactive = []
    for comp in components:
        if comp.size < 200 and comp.color not in [0, 4, 5]:  # Not white, dark gray, black
            interactive.append(comp)

    # Sort by size (smaller = more likely interactive) and color uniqueness
    interactive.sort(key=lambda c: c.size)

    # Convert to click coordinates
    targets = []
    for comp in interactive:
        # Click center of component
        center_row = sum(r for r, c in comp.cells) // len(comp.cells)
        center_col = sum(c for r, c in comp.cells) // len(comp.cells)
        targets.append({
            "x": min(center_col * 2, 127),  # 0-127 range for agent
            "y": min(center_row * 2, 127),
            "color": comp.color,
            "size": comp.size,
        })

    return targets
```

**Key insight:** For VC33 level 1, the interactive "ZGd" and "zHk" sprites are likely small colored blocks (9=blue, 11=yellow, 7=orange) on a background of black (5) and borders (0, 4). Filtering by size + color should isolate them.

**But also:** Track which clicks produce frame changes. If a click at (x, y) causes `_describe_frame_change()` to return something other than "no visible change", that's a confirmed interactive element. Click it again (or nearby) to understand the mechanic.

### Priority 4: Try the ADCR Agent Instead of Explorer

The ADCR agent has several advantages the explorer lacks:

1. **Multi-turn conversation context** — continuity between steps
2. **Visual diff images** (image_diff utility) — shows what changed, highlighted
3. **JSON retry with RESET fallback** — doesn't waste actions on parse failures
4. **Strategy guidance** — "favor moves before clicking"
5. **"NEW LEVEL!!!!" reinforcement** — positive signal on score increase

Even at 0 score, the ADCR agent's architecture is more sound for this task. The explorer was designed as a simpler baseline.

**Quick experiment:** Run `--agent adcr` with the current thinking-disabled baseline. Compare action diversity and click targeting to explorer.

### Priority 5: Enable Vision for Click Games

`use_vision=False` is set because "MLX models are text-only." This is true for the Qwen3.5-35B MLX adapter. But there are options:

**Option A: Use a cloud vision model for VC33/FT09 only.**
Route click games to Anthropic/OpenAI API (the project already has `anthropic` and `openai` in dependencies) while keeping MLX for LS20. The scoring formula is quadratic — a single level solved is worth more than 40 actions of 0-score exploration.

**Option B: Use Qwen-VL or similar vision model via MLX.**
Some vision models can run on Apple Silicon via MLX. Even a smaller vision model might perform better on click games than a larger text-only model.

**Option C: Convert frames to structured text descriptions instead of raw JSON.**
Instead of dumping the 64x64 grid as JSON (8,000 tokens), describe it spatially:
```
Objects found:
- Small blue block (color 9, 4x3) at position (28, 14)
- Small yellow block (color 11, 3x3) at position (45, 22)
- Large black border (color 5) around edges
- Gray background (color 3) filling most of grid
```
This is 50 tokens vs 8,000 tokens and contains MORE useful information.

### Priority 6: Fix the Explorer Convert Prompt

If you keep the explorer agent, add coordinate range to `convert.prompt`:

```
For ACTION6 (click), provide x and y coordinates in the 0-127 range.
These will be divided by 2 to map to the 64x64 game grid.
To click on row R, column C of the grid, use x = C * 2, y = R * 2.
```

This is a one-line fix that prevents the LLM from guessing random coordinate ranges.

---

## Quick Wins (Can Implement Today)

| Change | Impact | Effort |
|--------|--------|--------|
| Fix convert prompt coordinate range | Correct click targeting when LLM chooses to click | 1 line |
| Frame-as-structured-description instead of JSON dump | 160x token reduction, better spatial info | ~30 lines in `formatting.py` |
| Filter click targets by size/color (skip structural) | Brute-force clicks hit interactive sprites | ~20 lines in object detection |
| Track click effects per position | Agent learns which cells respond to clicks | ~10 lines in explorer agent |
| Route VC33 directly to click phase (skip probe) | Save 5 actions on a game where only clicks work | ~5 lines in `_probe_step` |
| ADCR agent comparison run | May outperform explorer immediately | CLI flag change |

## Medium-Term (This Week)

| Change | Impact | Effort |
|--------|--------|--------|
| Local game server | 2-5x faster experiments + debug logging | ~20 lines + env var |
| Programmatic state graph exploration | Breaks loops, systematic coverage, no LLM waste | ~150 lines new class |
| Cloud vision model for click games | Actually "see" interactive elements | Config + routing logic |
| Hybrid architecture: programmatic core + LLM for hypotheses | Matches competition-winning approach | ~300 lines refactor |

## Architectural Recommendation

The current autoresearch loop (researcher proposes → executor implements prompt/memory tweaks → benchmark → compare) is well-suited for parameter optimization but not for the architectural shift needed here. The next breakthrough won't come from idea #19 in the queue. It'll come from:

1. **Start a local server** so you can iterate in seconds not minutes
2. **Build a programmatic explorer** that covers the state space systematically
3. **Use the LLM as an oracle** called every 10-20 actions for high-level reasoning, not a per-step controller
4. **Enable vision or structured descriptions** for click games
5. **Focus on VC33 level 1** — 6 clicks to solve, highest ROI for first score

The speed improvements (131s → 4.8s/action) and JSON fix (15% → 100% parse) were real engineering wins. But they optimized the wrong architecture. The competition results are unambiguous: programmatic exploration crushes LLM reasoning for these games.

---

## Files Reference

| File | Purpose | Key Lines |
|------|---------|-----------|
| `src/arcagi3/agent.py:503-509` | The `//2` click coordinate transform | Only transform in the chain |
| `src/arcagi3/agent.py:383-384` | `_run_session_loop` entry | Main game loop |
| `src/arcagi3/game_client.py:30` | `ARC_URL_BASE` default | Remote API target |
| `src/arcagi3/autoresearch/runner.py:109` | `use_vision=False` | Why agent can't see |
| `src/arcagi3/explorer_agent/prompts/convert.prompt` | Missing coordinate range | Click targeting bug |
| `src/arcagi3/explorer_agent/agent.py:150-151` | Probe skips ACTION6 | Wastes 5 actions for click games |
| `src/arcagi3/utils/formatting.py:26-37` | `grid_to_text_matrix` | Raw JSON, 8000 tokens |
| `arcengine/camera.py:318-350` | `display_to_grid()` | Camera coordinate transform |
| `arcengine/enums.py:45-49` | `ComplexAction(x: 0-63, y: 0-63)` | Coordinate validation |
| `environment_files/vc33/*/vc33.py` | VC33 game source | Click handling, sprite tags |
