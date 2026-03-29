# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 032): 12 consecutive experiments at 0.6667. DFS/BFS/greedy all fail for ls20 (health=3 lives, dies in 3 moves without pickups). THE KEY INSIGHT: ls20 has "iri" pickup items (color 11) that prevent health drain. The agent MUST detect and navigate toward these to survive >3 moves. Without pickup-chaining, no exploration strategy can work. Test #1 (pickup detection) before anything else.**

---

### 1. [Navigation Strategy] LS20 pickup-first survival — detect "iri" items (color 11) within 2 moves
- **Hypothesis**: Source code analysis reveals ls20 health = 3 lives. Each move WITHOUT collecting an "iri" pickup (color 11, hollow 3x3 square) costs 1 life → death in 3 moves. Collecting a pickup prevents health drain for that move. The agent MUST navigate toward pickups first to survive. Detect color 11 objects near the player center (20,32) and move toward the nearest one within 2 moves. This extends the exploration budget from 3 moves to potentially unlimited (if pickups are chained).
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. `_detect_pickups(grid)`: Scan for color 11 objects (hollow 3x3 squares). Return list of (row, col) positions.
  2. In `_choose_action()` for ls20: ALWAYS prioritize moving toward the nearest pickup over any other action. If no pickup visible within 2 moves, explore toward the direction with the most green cells (might reveal a pickup after scrolling).
  3. After collecting a pickup (health not drained), the agent gets another 3-move budget to reach the next pickup.
  4. This creates a "pickup chain" navigation: pickup → pickup → pickup → ... → goal.
- **Target game**: ls20
- **Expected impact**: Extends survival from 3 moves to potentially 20+ moves (if pickups exist). Prerequisite for any ls20 scoring.

### 2. [Puzzle Logic] LS20 state modifier tracking — understand shape/color/rotation items
- **Hypothesis**: ls20 level completion requires visiting goals with the CORRECT player state (shape, color, orientation). State modifiers change these: "gsu" items change shape, "gic" items change color, "bgt" items rotate. The agent should detect these items on the grid and track its current state to know when it matches a goal.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track player state: `{shape_index, color_index, rotation}`. When stepping on a modifier (detected by frame change pattern), update state. When near a goal, check if current state matches.
- **Target game**: ls20
- **Expected impact**: Enables goal-matching. Without state tracking, the agent can't know when to visit goals.

### 3. [Navigation Strategy] LS20 death-and-learn — use repeated resets to map the maze
- **Hypothesis**: With health=3 and frequent deaths, the agent gets many short attempts. Each attempt reveals ~3 moves of information. With 500 max actions, the agent gets ~150 attempts. By recording what it learned from each death (which directions worked, where pickups were, where walls are), it can gradually build a map and eventually find the path.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After GAME_OVER (reset): preserve the wall map and pickup locations from the last attempt. On the next attempt, use this knowledge to plan a better path. Gradually extend explored range with each death.
- **Target game**: ls20
- **Expected impact**: Turns repeated deaths into a learning signal. Each death contributes to a more complete map.

### 4. [Navigation Strategy] LS20 ACTION5 not available — remove from strategy
- **Hypothesis**: Source code confirms ls20 only has ACTION1-4 (directional moves). ACTION5 (perform) is NOT available. Remove it from all ls20 strategies. Items are collected by moving onto them, not by performing.
- **Files to modify**: Update play_strategy.md, remove ACTION5 references for ls20
- **Target game**: ls20
- **Expected impact**: Prevents wasting actions on unavailable perform.

### 2. [Puzzle Logic] VC33 level 3: visually inspect the puzzle via arc CLI
- **Hypothesis**: After 6 experiments (022-027) trying to crack level 3 programmatically, the scoring condition is still unknown. The executor should visually inspect level 3 via `arc state --image` to understand what the ACTUAL goal looks like. The markers, bars, and buttons are known — but what does "solved" look like? Is it bar height equality? A specific pattern? Something else entirely?
- **Files to modify**: None initially — investigation
- **Changes**: Play vc33, solve levels 1-2, then inspect level 3:
  ```bash
  arc start vc33 --max-actions 200
  # Auto-solve levels 1-2 (existing strategy handles these)
  arc state --image    # SEE level 3 — what's the goal?
  # Click buttons one at a time and observe
  arc state --image    # What changed? Is it getting closer to "solved"?
  arc end
  ```
- **Target game**: vc33 level 3
- **Expected impact**: Visual understanding of what "solved" means for level 3.

### 3. [Navigation Strategy] LS20 scrolling map builder — accumulate explored terrain
- **Hypothesis**: ls20's view scrolls 52 cells per move. The agent only sees a portion of the maze at a time. By tracking which cells have been explored (building a partial map from sequential frames), the agent can: (a) know where it has been, (b) avoid revisiting explored areas, (c) find the frontier of unexplored paths to navigate toward.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Maintain a large accumulated map (larger than 64x64 grid) by stitching frames together based on scroll direction. Track player position in absolute coordinates. BFS on the accumulated map instead of just the current frame.
- **Target game**: ls20
- **Expected impact**: Solves the "partial visibility" problem. Agent can plan paths through previously-seen areas.

### 4. [Navigation Strategy] LS20 health monitoring — white bar parsing
- **Hypothesis**: ls20 has a white health bar (exp 028). Monitor it to avoid GAME_OVER. When health is low, prioritize reaching the goal over exploring.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Scan for white bar (color 0 or 15?) in status area. Parse remaining health. When health < 30%, switch to exploitation: follow shortest known path to nearest goal.
- **Target game**: ls20
- **Expected impact**: Prevents death, preserves score from completed actions.

### 3. [Action Efficiency] VC33 levels 1-2: solve in minimum clicks
- **Hypothesis**: Levels 1-2 are solved but may use more clicks than the human baseline (6 and 13). By looking at the image and understanding the exact puzzle state, the executor could solve in fewer clicks, improving per-level scores.
- **Strategy change**: Add to vc33 strategy: "On balance puzzle levels: count the exact gap between boundaries. Each click adjusts by ~1 unit. Click exactly `gap` times — no more."
- **Target game**: vc33
- **Expected impact**: Better per-level score through fewer wasted clicks.

### 4. [Navigation Strategy] LS20: look for player character and goal indicators
- **Hypothesis**: Claude Code with vision can SEE the ls20 grid. It should identify: (1) the player character (unique-looking entity), (2) goal indicators (doors, exits, bright objects), (3) obstacles (walls, barriers), (4) collectibles (keys, health). Then navigate purposefully toward the goal.
- **Strategy change**: Add to ls20 strategy: "First, identify yourself on the grid — look for a small, unique entity (often a different color from surroundings). Then look for potential goals: doors, exits, bright/distinct objects on the edges. Navigate toward them while avoiding obstacles. Use `perform` when you reach a goal."
- **Target game**: ls20
- **Expected impact**: First ls20 score. Even solving level 1 (29 baseline) would add to the average.

### 5. [Hypothesis Testing] VC33: try ONE click and reason about what changed
- **Hypothesis**: Instead of clicking multiple times before reasoning, click once, view the before/after difference, and reason about what the click did. This maximizes information per click (which costs a life).
- **Strategy change**: Add: "After EVERY click, view the frame. Compare to what you remember from before. Ask yourself: what changed? What does this tell me about the puzzle mechanic? Plan your next click based on this understanding."
- **Target game**: vc33
- **Expected impact**: Fewer wasted clicks, faster puzzle understanding.

### 6. [Puzzle Identification] VC33: identify puzzle type from first frame
- **Hypothesis**: Each vc33 level has a different puzzle layout but follows patterns. By classifying the puzzle type from the first frame (horizontal balance, vertical bar chart, sorting, etc.), the executor can immediately apply the right strategy.
- **Strategy change**: Add: "On the first frame of each level, classify the puzzle: (a) Two regions with a divider → balance puzzle (click the button that converges). (b) Vertical bars with buttons at bottom → bar chart (adjust each bar to target height). (c) Other → explore carefully with single clicks."
- **Target game**: vc33
- **Expected impact**: Faster level starts, fewer wasted exploratory clicks.

### 7. [Level Progression] VC33: carry mechanics knowledge across levels
- **Hypothesis**: vc33 levels share common mechanics (color 9 = buttons, clicking adjusts things). The executor should remember what worked on previous levels and apply it to new ones, adapting as needed.
- **Strategy change**: Add: "After solving a level, note what you learned: which objects were interactive, what the mechanic was, how many clicks were needed. Apply this knowledge to the next level — it's probably a variation of the same mechanic."
- **Target game**: vc33
- **Expected impact**: Faster adaptation on new levels.

### 8. [Visual Analysis] LS20: identify health bar and monitor it
- **Hypothesis**: LS20 has health drain. The executor should identify the health indicator (probably a colored bar at the top or bottom) and monitor it to avoid dying. When health is low, stop exploring and try to find a health restore or the goal.
- **Strategy change**: Add: "Look for a health/life bar (often colored bar at the edge of the screen). Monitor it after each move. If health drops below ~30%, prioritize finding the goal or a health restore rather than exploring."
- **Target game**: ls20
- **Expected impact**: Prevents GAME_OVER, preserves more actions for solving.

### 9. [Click Strategy] VC33: count remaining lives before acting
- **Hypothesis**: The health bar in vc33 (row 0: orange/yellow) shows remaining lives. The executor should check it before committing to a strategy. If lives are low and the current level is unsolved, be very conservative.
- **Strategy change**: Add: "Check the health bar (top of screen) regularly. If you've used more than half your lives without solving the current level, switch to conservative mode — only click objects you're confident about."
- **Target game**: vc33
- **Expected impact**: Preserves score from solved levels.

### 10. [Navigation Strategy] LS20: try perform action at interesting locations
- **Hypothesis**: LS20's `perform` action might trigger interactions at specific locations (keys, doors, switches). The executor should try `perform` when it sees a distinct object or when movement stops (indicating a wall or barrier).
- **Strategy change**: Add: "When you see a distinct object or reach a dead end, try `perform`. It might collect an item, open a door, or trigger a mechanism. Don't use `perform` randomly — save it for when you think you've reached something important."
- **Target game**: ls20
- **Expected impact**: Discovers interactive elements in ls20.

### 11. [Visual Analysis] VC33 level 3: compare left vs right halves for goal state
- **Hypothesis**: Many visual puzzles show the current state and goal state side by side. Level 3's bar chart might have a reference pattern on one side and the adjustable bars on the other. The executor should look for this dual structure.
- **Strategy change**: Add: "Look for a comparison structure — is half the screen showing a 'goal' pattern and the other half the 'current' state? If so, click buttons to make the current match the goal."
- **Target game**: vc33
- **Expected impact**: Identifies goal state for bar chart levels.

### 12. [Action Efficiency] All games: plan before acting
- **Hypothesis**: Every action costs either a life (vc33) or health (ls20). Planning 2-3 moves ahead reduces wasted actions.
- **Strategy change**: Add: "Before each action, state your plan: 'I will click X because I expect Y to change, which moves me toward the goal of Z.' If you can't articulate a plan, observe more carefully before acting."
- **Target game**: all
- **Expected impact**: More deliberate, fewer wasted actions.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-027**: Six experiments on vc33 level 3 bar chart. All reverted. Scoring condition still unknown.
- **Stategraph 028**: ls20 visual investigation — maze game, player=blue cross, green=path, yellow=walls.
- **Stategraph 029**: Green density heuristic — too greedy for large maze. Reverted.
- **Stategraph 030**: BFS maze solver — invisible walls break visual pathfinding. Reverted.
- **Stategraph 031**: Wall-hit avoidance + 5000 actions — still GAME_OVER from health drain. Reverted.
- **Stategraph 032**: DFS corridor following — corridors don't lead to goals. Reverted. "Score stable at 0.6667 for 12 experiments."
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
