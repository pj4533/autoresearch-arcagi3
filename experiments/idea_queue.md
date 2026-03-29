# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 030): ls20 has INVISIBLE WALLS — visual green cells ≠ actual walkability. BFS/A* on visual grid fails. The stategraph's empirical trial (try move, observe if blocked) is the correct approach. But it explores too randomly. Need: (1) directional bias toward goal objects, (2) wall memory from failed moves, (3) depth-first exploration instead of breadth-first. Also: health management critical.**

---

### 1. [Navigation Strategy] LS20 empirical wall memory + goal-directed bias
- **Hypothesis**: Exp 030 proved visual pathfinding fails (invisible walls). The stategraph's trial approach is correct but too random. Fix: combine empirical wall testing (stategraph) with directional bias toward visible goal objects. When the agent tries a move and it's blocked (same state hash), record that direction as "wall" at that position. When choosing next move, prefer directions that: (a) are not known walls, (b) point toward visible goals, (c) lead to unvisited states.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. `_detect_goal_direction(grid)`: Scan grid for maroon/gray objects. Return relative direction (up/down/left/right) from center (20,32).
  2. In `_choose_action()` for movement games: instead of trying untried actions in order, try the direction toward the nearest goal FIRST. If blocked, try the perpendicular directions. If all blocked, backtrack.
  3. Record empirical wall map: `blocked_directions[state_hash] = set(["ACTION1", "ACTION3"])` when a move produces no state change.
  4. Use wall map to avoid retrying known-blocked directions.
  5. When a goal object is visible, bias strongly toward it (priority 0). When no goal visible, use DFS-like exploration (go deep before backtracking).
- **Target game**: ls20
- **Expected impact**: Combines correct walkability testing with intelligent direction selection. Fewer wasted moves → survives longer → reaches goals.

### 2. [Navigation Strategy] LS20 depth-first exploration — go deep before backtracking
- **Hypothesis**: The stategraph tries all directions from each state breadth-first. For a maze, DFS is better: go as deep as possible in one direction, only backtrack when stuck. This covers more ground with fewer total moves and is more likely to find distant goals.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_choose_action()` for movement games: when the last move succeeded (new state), try the SAME direction again. Only change direction when blocked. This creates a DFS-like exploration that follows corridors instead of ping-ponging.
- **Target game**: ls20
- **Expected impact**: Faster maze traversal. Follows corridors efficiently.

### 3. [Navigation Strategy] LS20 perform at goal objects — try ACTION5 when near targets
- **Hypothesis**: ls20 has maroon blocks (keys) and gray boxes (doors/exits). When the player is adjacent to one (visible near center), `perform` (ACTION5) might collect/interact with it. The current agent never uses perform strategically.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After each move, check if maroon/gray objects are near the center (player position). If so, try ACTION5 (perform). This costs one action but might trigger level completion or item collection.
- **Target game**: ls20
- **Expected impact**: Discovers interact mechanic. Even basic perform-at-goals might solve levels.

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
- **Stategraph 022-027**: Six experiments on level 3 bar chart. Markers detected (11/14/15), buttons probed, per-column diff done. Scoring condition still unknown. Targeted clicking with gaps=[1,0,1,5] didn't score. "Some pairs require alternation." Moving focus to ls20.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
