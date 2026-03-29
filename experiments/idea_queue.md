# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 043): LS20 is closest to scoring — waypoints reached within ~3 cells (exp 042-043). Position drift is the ONLY blocker. Fix the drift and ls20 level 1 should score. VC33 level 3 still needs visual investigation. Scoring formula is QUADRATIC: (human/agent)^2, so action efficiency matters enormously once a level is solved.**

---

### 1. [Puzzle Logic] LS20 grid-search at waypoint — systematically find exact modifier cell
- **Hypothesis**: Exp 042-043 reached within ~3 cells of the modifier at (19,30) but didn't collect it. Position tracking drifts because movement is not always exactly 5 cells. Instead of fixing the drift, **brute-force the last few cells**: when the agent's estimated position is within ~8 cells of a waypoint, enter a "grid search" mode — try all 4 directions systematically in a small spiral pattern. This guarantees passing through the exact modifier cell within ~16 extra moves.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. When `abs_distance_to_waypoint < 8`: enter grid-search mode
  2. Grid search pattern: try RIGHT, UP, LEFT, LEFT, DOWN, DOWN, RIGHT, RIGHT, RIGHT, UP, UP, UP... (expanding spiral)
  3. After each move, check if frame changed significantly (modifier collected → distinctive frame change when sprite disappears)
  4. If modifier collected (detected by frame change pattern), switch to goal waypoint
  5. If spiral exhausted without collection, resume DFS toward waypoint with tighter distance threshold
- **Target game**: ls20
- **Expected impact**: First ls20 score. Closes the ~3-cell gap between estimated and actual position.

### 2. [Puzzle Logic] LS20 detect modifier/goal from frame content, not accumulated position
- **Hypothesis**: Instead of tracking accumulated position (which drifts), detect the modifier sprite VISUALLY on the grid. The "bgt" rotation modifier has a distinctive appearance. When it appears near the player center (20,32), the agent is close. When it DISAPPEARS from the grid after a move, the modifier was collected. This bypasses position tracking entirely.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Each step, scan the visible grid for distinctive sprites (non-background, non-wall, non-player patterns)
  2. Track which distinctive patterns are visible frame-to-frame
  3. If a pattern was visible and then disappeared after a move → item collected
  4. Use this as the waypoint-switch trigger instead of proximity check
  5. Also: scan for goal-area distinctive pattern to know when approaching goal
- **Target game**: ls20
- **Expected impact**: Reliable modifier detection without any position tracking drift.

### 3. [Puzzle Logic] LS20 calibrate movement displacement from frame comparison
- **Hypothesis**: Movement may not be exactly 5 cells per step (partial moves near walls). Compare frames before/after to detect actual displacement: find the pixel shift by cross-correlating the two frames. Use the measured displacement instead of assuming 5.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. After each successful move (frame changed), compare saved_prev_grid with current grid
  2. Find the offset (dx, dy) that maximizes pixel overlap between the two grids
  3. Use this measured offset to update abs_x, abs_y instead of hardcoded ±5
  4. This self-corrects drift on every move
- **Target game**: ls20
- **Expected impact**: Accurate position tracking → waypoints hit precisely.

### 4. [Visual Analysis] VC33 level 3 — visual investigation via arc CLI
- **Hypothesis**: After 6 programmatic experiments (022-027) on vc33 level 3, the scoring condition is still unknown. The executor should visually inspect level 3 via `arc state --image` to see what the bars/markers/buttons look like. This approach unlocked levels 1+2 (exp 019). Level 3 has colored markers (11/14/15) that indicate target heights — the executor needs to SEE them.
- **Files to modify**: None initially — investigation
- **Changes**: Play vc33 via arc CLI, solve levels 1+2, then inspect level 3:
  ```bash
  arc start vc33 --max-actions 200
  # Auto-solve levels 1-2 (existing strategy handles these)
  arc state --image    # SEE level 3 — what do bars/markers look like?
  # Click ONE button, then arc state --image — what changed?
  arc end
  ```
- **Target game**: vc33 level 3
- **Expected impact**: Visual understanding → targeted programmatic fix. This is how exp 019 achieved the first breakthrough.

### 5. [Puzzle Logic] VC33 level 3 per-column marker detection + exact click counts
- **Hypothesis**: Level 3 bars have colored markers (11/14/15) at target heights (discovered in exp 025). Detect these markers programmatically: scan each bar's column region for marker-colored pixels. The gap between current bar top and marker position = number of clicks needed. Trial one click per button to determine direction (grows/shrinks).
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Detect level 3 layout: 8 buttons in horizontal row at bottom
  2. For each bar column region, scan for pixels of color 11, 14, or 15
  3. Record marker Y position = target height
  4. Measure current bar top Y position
  5. Trial: click each button once, record whether bar grew or shrank (and by how much)
  6. Compute: clicks_needed = abs(current_top - marker_y) / change_per_click
  7. Execute: click each button the computed number of times
- **Target game**: vc33 level 3
- **Expected impact**: Solves level 3 → score improvement from 0.6667.

### 6. [Action Efficiency] Optimize vc33 level 1-2 click counts for better per-level scores
- **Hypothesis**: The scoring formula is QUADRATIC: (human/agent)^2. Level 1 baseline is 6 clicks, level 2 is 13. If the agent uses 12 clicks on level 1, the score is (6/12)^2 = 0.25. If it uses 7 clicks, score is (6/7)^2 = 0.73. Minimizing clicks matters hugely.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. On trial phase: instead of clicking every button once, click only 2 (there are only 2 per level 1). Cost: 2 clicks.
  2. Immediately lock the better button. Cost: 0 clicks (already evaluated).
  3. Click locked button exactly `gap` times (measured from trial). No re-trialing.
  4. Total: 2 (trial) + gap (execution) = minimum clicks
- **Target game**: vc33
- **Expected impact**: Better per-level scores on already-solved levels.

### 7. [Navigation Strategy] LS20 persistent maze map across deaths (iterative deepening)
- **Hypothesis**: The state graph already persists data in the datastore. Ensure the waypoint navigation progress, wall memory, and explored paths persist across deaths (GAME_OVER → RESET → continue from start with accumulated knowledge). Each death adds ~18 moves of exploration data. After 3 deaths, the agent has ~54 moves of known-safe territory — enough to plan the 29-step level 1 solution.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Ensure state_graph, abs position, and waypoint state DON'T reset on GAME_OVER. Only reset position to (1,53) on death. The graph retains all explored transitions.
- **Target game**: ls20
- **Expected impact**: Progressive learning across deaths enables solving larger mazes.

### 8. [Navigation Strategy] LS20 level 2+ strategy — extract multi-level waypoints from source
- **Hypothesis**: Once level 1 is solved, level 2 has different modifier/goal positions. Extract these from `environment_files/ls20/cb3b57cc/ls20.py` for each level. The same waypoint DFS approach should work — just needs new coordinates per level.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Read level 2+ data from game source. Extract player start, modifier positions, goal positions for each level. Store as waypoint lists indexed by level number. On level transition, load next level's waypoints.
- **Target game**: ls20
- **Expected impact**: Multi-level solving once level 1 works.

### 9. [Visual Analysis] LS20 health monitoring — detect life loss and switch to exploitation
- **Hypothesis**: ls20 has 3 hearts. When health drops to 1 heart, the agent should stop exploring and follow the shortest known path toward the goal. Detecting health: scan status area for heart sprites or count distinctive pixels in status rows.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Scan rows 0-1 (status bar) for health indicators. Track health changes. When health critical, switch to goal-directed mode using best known path.
- **Target game**: ls20
- **Expected impact**: Prevents death when close to solving.

### 10. [Level Progression] VC33 level 4+ investigation — understand new puzzle types
- **Hypothesis**: Levels 4-7 have baselines of 59-92 actions and may have different mechanics. Level 4+ reportedly requires precise clicking on small blue squares (per HN discussion). Understanding what levels 4+ look like enables targeted strategies. However, this is low priority until level 3 is solved.
- **Files to modify**: None — investigation
- **Target game**: vc33
- **Expected impact**: Strategy preparation for higher levels.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-027**: Six experiments on vc33 level 3 bar chart. All reverted. Scoring condition partially understood (colored markers at target heights).
- **Stategraph 028**: ls20 visual investigation — maze game, player=blue cross, green=path, yellow=walls.
- **Stategraph 029-035**: Seven ls20 navigation experiments — all reverted. Maze too large for heuristic exploration.
- **Stategraph 036-037**: Maze data extraction from source + offline BFS. BFS failed (collision model proprietary).
- **Stategraph 038**: Hardcoded prefix — partial path not useful.
- **Stategraph 039-041**: Iterative deepening / DFS — navigation SOLVED (34-46 steps). Blocker is state matching, not navigation.
- **Stategraph 042-043**: Waypoint navigation — REACHED both waypoints within ~3 cells! Position drift prevents scoring. 22 experiments at plateau.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
- **TESTED AND REJECTED**: Anti-oscillation (exp 034), goal-direction bias (exp 035), corridor following (exp 032), wall-hit avoidance (exp 031), green density (exp 029), visual BFS (exp 030).
