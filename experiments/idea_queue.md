# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 021 — score 0.6667): Levels 1+2 solved via trial-and-lock with re-trialing. Level 3 has 8 horizontal buttons — ALL show improvement=0. The `_measure_imbalance()` only counts GREEN cells. Level 3 likely uses different colors → green metric shows 0 even if buttons change the frame. Fix: use total cell change count as trial metric instead of green-only.**

---

### 1. [Puzzle Logic] Use total cell change as trial metric — not green-only
- **Hypothesis**: Exp 021 solved levels 1+2 (score 0.6667) but level 3 (8 horizontal buttons) shows improvement=0 for ALL buttons. The `_measure_imbalance()` counts only GREEN (color 3) cells. Level 3 likely uses different fill colors, so green metric reads 0 even though buttons DO change the frame. Fix: measure TOTAL cell changes between pre-click and post-click grids. The button that changes the most cells is the interactive one.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Add `_count_cell_changes(grid_before, grid_after)` → count cells where `grid_before[r][c] != grid_after[r][c]`
  2. In trial phase: save grid snapshot before each trial click, count changes after
  3. Lock the button with the MOST cell changes (not green imbalance improvement)
  4. Keep `_measure_imbalance()` as a secondary metric for re-trialing (plateau detection), but use cell change count for initial button selection
  5. Save pre-click grid in datastore: `context.datastore["pre_trial_grid"] = [row[:] for row in grid]`
- **Expected impact**: Detects interactive buttons regardless of color scheme → solves level 3+.

### 2. [Puzzle Logic] Color-agnostic imbalance for plateau detection
- **Hypothesis**: Even after fixing the trial metric, the plateau detection (re-trialing after 3 stale steps) still uses green-only `_measure_imbalance()`. Level 3+ may plateau based on different colors. Use a generic "distribution variance" metric.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Replace `_measure_imbalance()` with a color-agnostic version:
  1. Find the most common non-background color in the grid (the "fill" color) — this auto-detects green, blue, red, etc.
  2. Count that color per sampled row
  3. Return max-min as imbalance (same logic, different color target)
- **Expected impact**: Plateau detection works for any color scheme.

### 3. [Puzzle Logic] Investigate level 3 visually — what do 8 horizontal buttons look like?
- **Hypothesis**: Level 3 has "8 horizontal buttons" and none improve green imbalance. Visual investigation would reveal: what's the puzzle structure? Different fill colors? Different mechanic entirely? Are the 8 buttons controlling 8 independent regions?
- **Files to modify**: None initially — investigation
- **Changes**: Use arc CLI to reach level 3 (solve levels 1+2 first, ~30 actions) and inspect:
  ```bash
  arc start vc33 --max-actions 300
  # Level 1+2 auto-solve via existing strategy
  arc state --image    # See level 3 layout
  # Click a few of the 8 buttons and observe
  arc end
  ```
- **Expected impact**: Understanding level 3 → targeted fix.

### 4. [Life Management] Health bar tracking + stop on low lives
- **Hypothesis**: When level 3 can't be solved, the agent wastes remaining lives → GAME_OVER → might lose accumulated score. Tracking health and stopping early preserves the score from levels 1+2.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add `_parse_health(grid)` → count color 7 (orange) cells in row 0. When health < 5 clicks remaining AND no progress on current level → stop clicking (return None or repeat last known-good action).
- **Expected impact**: Preserves level 1+2 score instead of GAME_OVER.

### 5. [Puzzle Logic] Try 2-button combinations if single buttons have no effect
- **Hypothesis**: If all 8 single-button trials show 0 cell changes, the puzzle might require COMBINATIONS: clicking A then B produces an effect neither alone does. With 8 buttons, C(8,2)=28 pairs. At 2 clicks per pair, test ~20 pairs with 50 lives.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After single-button trials all show 0: enter combination phase. Try pairs (A,B), measure total cell changes. Lock the pair with most changes.
- **Expected impact**: Handles multi-button interaction puzzles.

### 6. [Frame Analysis] Investigate ls20 visually — understand navigation mechanics
- **Hypothesis**: Visual investigation unlocked vc33. Same approach for ls20 might reveal: player position, walls, objectives, health indicators.
- **Files to modify**: None initially — investigation
- **Changes**: Use arc CLI to explore ls20 visually.
- **Expected impact**: Understanding ls20 → targeted strategy.

### 7. [Action Priority] Optimize click count — stop when imbalance hits 0
- **Hypothesis**: The agent keeps clicking until score changes (level transition). But if it detects imbalance=0 (boundaries equalized), it should stop to save lives for later levels.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After each click in balance mode, check if imbalance <= 1. If so, wait for score change instead of continuing to click.
- **Expected impact**: Fewer wasted clicks, more lives for later levels.

### 8. [Puzzle Logic] Level 3 might need different fill color detection
- **Hypothesis**: Levels 1+2 use green (color 3). Level 3 might use blue (color 9), orange (color 7), or other colors. The imbalance metric must auto-detect the fill color.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Before measuring imbalance, scan the grid for the dominant non-background, non-status-bar, non-button color. Use that as the fill color.
- **Expected impact**: Handles any fill color.

### 9. [Cross-Level Transfer] Remember puzzle parameters across levels
- **Hypothesis**: Carry forward: button color (always 9?), fill color, puzzle type. Speeds up detection on new levels.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: On level transition, save puzzle parameters. On new level, try the same parameters first before full re-detection.
- **Expected impact**: Faster per-level startup.

### 10. [Puzzle Logic] Handle vertical/diagonal dividers
- **Hypothesis**: Some levels might have vertical or diagonal dividers instead of horizontal. Current detection only finds horizontal bars.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add vertical bar scan (columns with >40% uniform color). Add diagonal check.
- **Expected impact**: Handles non-horizontal layouts.

### 11. [Puzzle Logic] Multiple independent balance regions
- **Hypothesis**: Level 3 with 8 buttons might have 4 independent balance regions (each with 2 buttons). Each region needs to be balanced independently.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Detect multiple divider bars. For each region between bars, find buttons and measure imbalance independently. Solve each region in sequence.
- **Expected impact**: Handles multi-region puzzle layouts.

### 12. [Puzzle Logic] LS20 player detection + directed exploration
- **Hypothesis**: LS20 has a player entity. Detecting and tracking player position enables directed movement strategies.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Find objects that move when movement actions are taken. Track position over time.
- **Expected impact**: Purposeful navigation.

### 13. [Frame Analysis] Grid structure classifier — detect puzzle type
- **Hypothesis**: Different levels may be fundamentally different puzzle types. Route to appropriate strategy.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: `_classify_puzzle(grid)` returns: "balance", "sorting", "matching", "unknown".
- **Expected impact**: Multi-strategy support.

### 14. [Life Management] GAME_OVER prevention — safe fallback
- **Hypothesis**: When stuck on an unsolvable level, stop clicking to preserve score.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track consecutive 0-improvement clicks. After 15, stop clicking entirely.
- **Expected impact**: Preserves accumulated score.

### 15. [Puzzle Logic] Level 2 cycling optimization — detect the cycle pattern
- **Hypothesis**: Level 2 needed button cycling: A→plateau→B→plateau→A→SCORE. If the agent can detect the cycling pattern faster (recognize plateau after 1-2 steps instead of 3), it saves clicks.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Reduce stale threshold from 3 to 2 for re-trialing. Or detect when imbalance starts increasing and re-trial immediately.
- **Expected impact**: Fewer wasted clicks on level 2.

---

## Completed

- **Stategraph 001-018**: All score 0.
- **Stategraph 019**: **BREAKTHROUGH** avg=0.3333, vc33=1.0. Balance puzzle solved level 1.
- **Stategraph 020**: Generalized balance — detected level 2 but wrong button. Reverted.
- **Stategraph 021**: **IMPROVED** avg=0.6667, vc33=2.0. Trial-and-lock with re-trialing solved levels 1+2. Level 3: 8 buttons, improvement=0. GAME_OVER.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
