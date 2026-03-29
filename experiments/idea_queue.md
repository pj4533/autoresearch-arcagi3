# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, CRITICAL FIX): THE PLAYER ENTITY IS NOT "hep" AT (1,53)! Deep source code analysis reveals the movable player is sprite "pca" (tag "caf"), which starts at (39,45) in level 1. The agent has been tracking the WRONG sprite's position and navigating in the WRONG DIRECTION. From (39,45), the modifier at (19,30) is 4 LEFT + 3 UP — not right! Fix: change starting position to (39,45) and recalculate all waypoint directions.**

---

### 1. [Puzzle Logic] LS20 CRITICAL: Fix player starting position — it's (39,45) not (1,53)!
- **Hypothesis**: **THE FUNDAMENTAL BUG.** Source code analysis (line 1350: `self.mgu = self.current_level.get_sprites_by_tag("caf")[0]`) reveals the movable player entity is the sprite with tag "caf" = sprite named "pca". In level 1, "pca" is placed at **(39, 45)** — NOT the "hep" sprite at (1, 53) which is actually a flash overlay (tag "nfq", used as `self.nlo`).

  **ALL experiments using position tracking from (1,53) were navigating in the WRONG DIRECTION:**
  - Modifier (19,30) is to the LEFT of (39,45), not RIGHT of (1,53)
  - Goal (34,10) is to the LEFT and UP of (39,45)
  - Exp 042-043 went RIGHT (increasing x from 39→54), moving AWAY from modifier at x=19
  - The "reaching within 3 cells" was coincidental — true position was ~35 cells away

  **Proof all items are on the same 5-cell grid:**
  - All 14 items across 7 levels have x≡4 mod 5 and y≡0 mod 5
  - Goal completion (nje()) requires EXACT position match: `self.mgu.x == ywm.x`
  - Starting positions per level: L1=(39,45), L2=(29,40), L3=(9,45), L4=(54,5), L5=(54,50), L6=(24,50), L7=(14,10)

- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  ```python
  # OLD (WRONG — hep sprite, which is the flash overlay):
  abs_x, abs_y = 1, 53

  # NEW (pca sprite, the actual player collision entity):
  # Level 1 starting position:
  abs_x, abs_y = 39, 45
  ```

  **Per-level data (sprite "pca" positions from source code):**
  | Level | Start | Modifier | Goal(s) | Mod direction |
  |-------|-------|----------|---------|---------------|
  | 1 | (39,45) | (19,30) | (34,10) | 4L + 3U |
  | 2 | (29,40) | (49,45) | (14,40) | 4R + 1D |
  | 3 | (9,45) | (49,10) | (54,50) | 8R + 7U |
  | 4 | (54,5) | NONE | (9,5) | — |
  | 5 | (54,50) | (19,40) | (54,5) | 7L + 2U |
  | 6 | (24,50) | (19,25) | (54,50),(54,35) | 1L + 5U |
  | 7 | (14,10) | (54,20) | (29,50) | 8R + 2D |

- **Target game**: ls20
- **Expected impact**: First ls20 score. With correct starting position, the waypoint DFS navigates in the RIGHT direction. Items are exactly reachable (all on same 5-cell grid). Level 1 solution: start(39,45) → 4L+3U → modifier(19,30) → 3R+4U → goal(34,10).

### 2. [Puzzle Logic] LS20 avoid re-collecting modifier after first collection
- **Hypothesis**: The bgt modifier is NOT removed when collected (stays in the level). Each walk-through cycles tuv by +1 mod 4. Level 1 needs exactly tuv=0 at goal (initial tuv=3, so 1 collection: 3→0). If DFS backtracks through modifier position, tuv corrupts (0→1→2→3...). Fix: after collecting modifier, add its position to a "blocked" list that DFS avoids.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After reaching modifier position AND frame change detected (player rotation), add modifier position to blocked set. DFS won't try moves that lead to blocked positions.
- **Target game**: ls20
- **Expected impact**: Prevents state corruption from multiple modifier collections.

### 3. [Puzzle Logic] LS20 detect modifier collection from player rotation change
- **Hypothesis**: The bgt modifier stays visible but the player sprite rotates on collection. Detect collection by comparing player center pixels before/after moving through modifier area. If visual appearance changed (rotation), modifier was collected → switch to goal waypoint.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After each move near modifier area, compare player center pixels. If changed, switch waypoint.
- **Target game**: ls20
- **Expected impact**: Reliable waypoint switching.

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
- **Stategraph 042-043**: Waypoint navigation — estimated "near" both waypoints but actually navigating WRONG DIRECTION (true start was (39,45), not (1,53)).
- **Stategraph 044**: Visual target detection + grid alignment analysis — confirmed items not on (1,53) grid. 24 experiments at plateau.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
- **TESTED AND REJECTED**: Anti-oscillation (exp 034), goal-direction bias (exp 035), corridor following (exp 032), wall-hit avoidance (exp 031), green density (exp 029), visual BFS (exp 030).
- **CORRECTED (exp 044 insight)**: Items NOT on (1,53) grid because **(1,53) is the WRONG starting position!** The "hep" sprite at (1,53) is a flash overlay (tag "nfq" → self.nlo). The actual movable player entity is "pca" sprite (tag "caf") starting at **(39,45)** in level 1 (source line 1350: `self.mgu = get_sprites_by_tag("caf")[0]`). From (39,45), ALL items are perfectly grid-aligned: x≡4 mod 5, y≡0 mod 5. This is a **1-line fix**.
