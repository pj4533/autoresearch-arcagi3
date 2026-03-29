# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 040): LS20 MAZE NAVIGATION SOLVED (34 steps > 29 baseline). But still score 0! ls20 requires collecting MODIFIERS (shape/color/rotation items) and visiting goals with correct player STATE. The next challenge is: detect modifiers, track player state, visit goals in correct state. This is the same progression as vc33: mechanics solved → now solve the puzzle logic.**

---

### 1. [Puzzle Logic] LS20 visual investigation of modifiers — what do they look like?
- **Hypothesis**: Exp 040 proved navigation works (34 steps > 29 baseline) but scoring needs state modifiers. The agent needs to detect and collect shape/color/rotation items before visiting goals. Use arc CLI to visually investigate: what do modifiers look like on the grid? What happens to the player's appearance when a modifier is collected? Are goals visually marked with the required state?
- **Files to modify**: None initially — investigation via arc CLI
- **Changes**: Play ls20 via arc CLI with max actions:
  ```bash
  arc start ls20 --max-actions 100
  arc state --image    # See starting grid — identify colored objects that aren't walls/paths
  # Navigate around, look for items that aren't green/yellow/blue
  arc action move_right
  arc state --image    # Did we pick something up? Did player appearance change?
  arc end
  ```
  Key questions: (1) What colors are modifier items? (2) What does the player look like before/after collecting one? (3) Are goals marked with a required state indicator?
- **Target game**: ls20
- **Expected impact**: Understanding modifiers → targeted collection strategy → first ls20 score.

### 2. [Puzzle Logic] LS20 detect modifier items by color — from game source data
- **Hypothesis**: The game source code defines modifier sprites: "gsu" (shape, color 0), "gic" (color, grid pattern), "bgt" (rotation, color pattern), "iri" (pickup, color 11). The agent can detect these on the grid by scanning for their distinctive colors/patterns. When the agent steps on one, record the state change.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. `_detect_modifiers(grid)`: Scan for non-wall, non-path, non-player colored objects. Colors to look for: 0 (gsu), 11 (iri), and distinctive patterns (gic, bgt).
  2. Track player state: `{shape_idx, color_idx, rotation}` in datastore
  3. After each move, check if the frame changed in a way consistent with modifier collection (player appearance changes)
  4. Prioritize moving toward detected modifiers
- **Target game**: ls20
- **Expected impact**: Enables modifier collection → correct state for goals.

### 3. [Puzzle Logic] LS20 goal-state detection — what state does each goal need?
- **Hypothesis**: Goals require the player to have a specific shape/color/rotation. This required state might be: (a) visible on the goal marker itself, (b) the same for all goals on a level, or (c) deducible from the available modifiers. If the goal marker shows the required state visually, the agent can plan which modifiers to collect.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After detecting a goal on the grid, analyze its visual appearance — does it show a specific shape/color/pattern that the player needs to match? Compare the goal's appearance to the player's current state.
- **Target game**: ls20
- **Expected impact**: Knowing the target state enables planning the modifier collection route.

### 4. [Puzzle Logic] LS20 collect-all-modifiers-then-visit-goals strategy
- **Hypothesis**: The simplest approach: navigate the maze, collect EVERY modifier item encountered, then visit goals. If the modifiers cycle through states (each collection changes state by +1), collecting the right number of each type produces the correct state. With DFS already navigating 34 steps, the agent likely passes through modifier locations.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: No change to navigation (DFS works). Add: after each move, check if a modifier was collected (frame change at player position). Track which modifiers were collected. After collecting all visible modifiers, navigate to goal positions.
- **Target game**: ls20
- **Expected impact**: If modifier collection is automatic (just walk over them), the DFS path may already collect some. Adding awareness completes the picture.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  The executor should do TWO things:

  **Step A: Extract walls from game code.**
  Read `environment_files/ls20/cb3b57cc/ls20.py`, find the level 1 ("krg") data. Look for sprites with tag "jdd" (walls, sprite "nlo") — their positions define the maze walls. Each wall sprite is 5x5 pixels. Also find: player start position, goal ("mae") positions, and modifier item positions.

  **Step B: Implement BFS pathfinding.**
  ```python
  def _ls20_compute_path(self):
      # Hardcode walls from game data (5x5 blocks)
      wall_positions = [...]  # from Step A
      # Build occupancy grid (64x64, True=blocked)
      blocked = [[False]*64 for _ in range(64)]
      for wx, wy in wall_positions:
          for dx in range(5):
              for dy in range(5):
                  if 0 <= wx+dx < 64 and 0 <= wy+dy < 64:
                      blocked[wy+dy][wx+dx] = True
      # BFS from start to goal, step size 5
      start = (1, 53)  # (x, y)
      goal = (34, 10)
      # Movement: up=(0,-5), down=(0,+5), left=(-5,0), right=(+5,0)
      from collections import deque
      queue = deque([(start, [])])
      visited = {start}
      moves = [(0,-5,"ACTION1"), (0,5,"ACTION2"), (-5,0,"ACTION3"), (5,0,"ACTION4")]
      while queue:
          (x,y), path = queue.popleft()
          if abs(x-goal[0]) < 5 and abs(y-goal[1]) < 5:
              return path  # Found!
          for dx, dy, action in moves:
              nx, ny = x+dx, y+dy
              if 0<=nx<64 and 0<=ny<64 and (nx,ny) not in visited:
                  # Check no wall in the 5x5 region around destination
                  if not blocked[ny][nx]:
                      visited.add((nx,ny))
                      queue.append(((nx,ny), path+[action]))
      return []  # No path found
  ```
  In `step()`: if ls20 game (available_actions has ACTION1-4): compute path once, store in datastore, execute one action per step.

  **Important**: The wall data must come from the ACTUAL game code, not my approximate list. Read the source file directly.
- **Target game**: ls20
- **Expected impact**: Computes exact path through known maze. No exploration, no oscillation, no traps from wrong moves. Human baseline 29 actions — BFS should find path of similar length.

### 2. [Navigation Strategy] LS20 anti-oscillation — commit to unexplored directions at junctions
- **Hypothesis**: Exp 033 found the agent "oscillates at maze junctions" — going back and forth between two directions instead of committing. With ~54 moves before death, the agent has budget but wastes it oscillating. Fix: at each junction, commit to the LEAST-VISITED direction and don't reverse for at least 3 steps.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Track `last_N_actions` (last 5 actions). If 2 of the last 3 are opposite (up/down or left/right), detect oscillation.
  2. On oscillation: pick the direction that leads to the LEAST-VISITED state (or an unvisited state) and lock it for 3 steps.
  3. Use `context.datastore["move_lock"]` to prevent direction changes during locked moves.
  4. After 3 locked moves, re-evaluate (check if state changed, new paths visible).
- **Target game**: ls20
- **Expected impact**: Eliminates wasted moves from oscillation. Agent explores deeper into maze branches.

### 2. [Navigation Strategy] LS20 trap detection + avoidance — identify what kills the agent
- **Hypothesis**: Exp 033 found death comes from TRAPS, not movement drain. The agent needs to detect which grid cells/states are traps and avoid them. After dying from a trap, record the state and direction that led to death. On the next attempt, avoid that transition.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. When GAME_OVER occurs (health loss), record: `{state_hash, last_action}` as a "trap transition"
  2. Store trap transitions in `context.datastore["trap_map"]`
  3. In `_choose_action()`: before selecting a direction, check if that direction from the current state is a known trap. If so, skip it.
  4. This accumulates trap knowledge across deaths (within the same game session).
- **Target game**: ls20
- **Expected impact**: Avoids known traps. With ~54 moves per life and trap avoidance, the agent can explore much further before dying.

### 3. [Navigation Strategy] LS20 progressive maze mapping — build map across deaths
- **Hypothesis**: Each death reveals ~18 moves of maze information. With 500 max_actions and ~54 moves per life, the agent gets ~9 full lives before max actions. That's ~9 × 18 = ~162 moves of exploration. By building a persistent map across deaths (recording which moves succeeded, which were walls, which were traps), the agent can gradually plan longer paths.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Persist `state_graph` across level resets (don't clear on death)
  2. After each death, the agent already knows all explored transitions + traps
  3. On restart, use the accumulated graph to plan: follow the longest known-safe path, then explore from the frontier
  4. This is essentially iterative deepening — each life explores further from the known-safe base
- **Target game**: ls20
- **Expected impact**: Turns ~9 deaths into a complete enough map to find the goal. Level 1 needs 29 moves — with 162 moves of total exploration, the agent should find the path.

### 4. [Puzzle Logic] VC33 level 3 — visual investigation via arc CLI (still untested)
- **Hypothesis**: After 6 programmatic experiments (022-027) on vc33 level 3, the scoring condition is still unknown. The executor should visually inspect level 3 via `arc state --image` to see what "solved" looks like. This approach unlocked levels 1+2 (exp 019).
- **Files to modify**: None — investigation
- **Changes**: Play vc33 via arc CLI, solve levels 1+2, then inspect level 3 visually.
- **Target game**: vc33 level 3
- **Expected impact**: Understanding what level 3 wants → targeted fix.

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
- **Stategraph 032**: DFS corridor following — corridors don't lead to goals. Reverted.
- **Stategraph 033**: Pickup-first + corridor — CORRECTED: health=3 hearts not per-move. Oscillation at junctions. Reverted.
- **Stategraph 034**: Anti-oscillation — "maze size is the fundamental blocker, not oscillation." Reverted. 14 experiments at plateau.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
- **NOT YET TESTED**: Known-maze pathfinding (#1 in queue — maze data extracted from game code).
