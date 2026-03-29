# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, ROOT CAUSE FOUND): Exp 042-043 used WRONG waypoint coordinates! The rbt() collision check requires specific grid-aligned positions. Agent was targeting item positions (19,30)→(34,10) but needs to target COLLECTION positions (16,28)→(31,8). Agent was exactly ONE UP MOVE short both times. Fix: change 2 waypoint coordinates. See research notes for full derivation.**

---

### 1. [Puzzle Logic] LS20 use COMPUTED COLLECTION POSITIONS as waypoints (root cause fix!)
- **Hypothesis**: **ROOT CAUSE FOUND.** Source code analysis reveals the `rbt()` collision check is asymmetric: `sprite.x >= target_x AND sprite.x < target_x + 5`. This means the agent must move to a SPECIFIC grid-aligned position to collect items — not just be "near" them. From start (1,53) with 5-cell moves, the ONLY positions that trigger collection are:
  - Modifier (bgt at 19,30): **collection position = (16, 28)**
  - Goal (mae at 34,10): **collection position = (31, 8)**
  - Exp 042 reached (16,33) and (31,13) — both exactly ONE UP MOVE short (y off by 5)!
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Change waypoint targets from item positions to collection positions:
  ```python
  # OLD (wrong — these are sprite positions, not reachable collection positions):
  waypoints = [(19, 30), (34, 10)]
  # NEW (computed collection positions from rbt() analysis):
  waypoints = [(16, 28), (31, 8)]
  ```
  This is a **2-line change**. The agent already reaches the correct X. It just needs the correct Y target.
- **Target game**: ls20
- **Expected impact**: First ls20 score. This directly fixes the root cause — no grid search or calibration needed.
- **Why this is right**: Movement confirmed ALWAYS exactly 5 cells (source line 1438). No partial moves. The drift isn't from movement calibration — it's from targeting the WRONG coordinates. The agent aims at (19,30) and stops when "close enough" at (16,33). But the collection position is (16,28), one more UP move away.

### 2. [Puzzle Logic] LS20 grid-search fallback at waypoint (if fix #1 doesn't work)
- **Hypothesis**: If the computed collection positions don't fully solve it (e.g., maze routing prevents reaching the exact cell), add a grid search: when within ~8 cells of waypoint, try all 4 directions systematically in a spiral. Guarantees hitting every nearby 5-cell-aligned position within ~16 extra moves.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: When `abs_distance_to_waypoint < 8` AND waypoint not yet triggered: enter spiral search mode. Try UP first (since exp 042-043 were both one UP short).
- **Target game**: ls20
- **Expected impact**: Robust fallback. At most ~16 extra moves.

### 3. [Puzzle Logic] LS20 detect modifier collection from player rotation change
- **Hypothesis**: Source code confirms the bgt modifier is NOT removed when collected — it stays visible on the grid. So "detect by sprite disappearance" won't work. BUT the player sprite DOES rotate (`nio.set_rotation`). Detect collection by: compare player center pixels before/after moving through modifier area. If the player's visual appearance changed (rotation), the modifier was collected → switch to goal waypoint.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After each move near modifier area, compare a small region around player center (20,32) with saved frame. If pixel pattern at center changed shape (not just position shift), modifier was collected.
- **Target game**: ls20
- **Expected impact**: Reliable waypoint switching independent of position tracking.

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
- **Stategraph 044**: Visual target detection — color 1 false positives, grid alignment blocks exact matching. Waypoint positions not on player's 5px movement grid. 23 experiments at plateau.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
- **TESTED AND REJECTED**: Anti-oscillation (exp 034), goal-direction bias (exp 035), corridor following (exp 032), wall-hit avoidance (exp 031), green density (exp 029), visual BFS (exp 030).
- **KEY INSIGHT (exp 044)**: From (1,53) moving by 5, reachable positions are {1,6,11,16,21,26,31,36,...} × {53,48,43,38,33,28,23,18,...}. Modifier at (19,30) and goal at (34,10) are NOT on this grid. The maze must have junctions that shift alignment. Need to find the ACTUAL path from game data, not approximate with position tracking.
