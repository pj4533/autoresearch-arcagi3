# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 022 — score 0.6667): Level 3 is a VERTICAL BAR CHART — gray bars of varying heights with 8 buttons at the bottom (one per bar). This is fundamentally different from levels 1-2 (horizontal balance). Row-based imbalance can't capture bar height. Need: (1) bar height measurement per column, (2) "bar height variance" as the imbalance metric, (3) trial-and-lock to find which button reduces variance.**

---

### 1. [Puzzle Logic] Bar height metric for level 3 — measure column heights not row distribution
- **Hypothesis**: Exp 022 confirmed level 3 is a vertical bar chart (gray bars of different heights, 8 buttons at bottom). The current `_measure_imbalance()` counts green cells per row — completely wrong for vertical bars. The correct metric is BAR HEIGHT VARIANCE: measure the height of each gray column (scan down from top, count gray cells), compute max-min or variance. The button that reduces this variance is the correct one.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Add `_measure_bar_heights(grid)`: for each column region (between button x-positions), scan down from top row (below status bar) counting non-background cells. Return list of heights.
  2. Add `_bar_height_variance(heights)`: return max(heights) - min(heights). This is the bar chart imbalance.
  3. In trial phase for level 3+: use bar_height_variance as the trial metric (instead of green row imbalance). Save heights before click, compare after. The button that reduces variance most gets locked.
  4. Auto-detect puzzle type: if buttons are arranged horizontally at the bottom AND grid has vertical bars above them → use bar height metric. If buttons are scattered with horizontal regions → use row-based green metric.
  5. For plateau detection: re-measure bar_height_variance. Plateau = variance unchanged for 3 steps.
- **Expected impact**: Solves vertical bar chart puzzles like level 3. Combined with existing row-based metric for levels 1-2, covers both puzzle types.

### 2. [Puzzle Logic] Auto-detect puzzle type — horizontal balance vs vertical bar chart
- **Hypothesis**: Levels 1-2 are horizontal balance puzzles (green fill, horizontal divider). Level 3 is a vertical bar chart (gray bars, buttons at bottom). The agent needs to detect WHICH type of puzzle it's facing and use the appropriate metric. A simple heuristic: if buttons are in a horizontal row at the bottom → bar chart. If buttons are above/below a horizontal divider → horizontal balance.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add `_detect_puzzle_type(grid, buttons)`:
  1. Check button Y positions: if all within 2 rows of each other AND near bottom → "bar_chart"
  2. Check for horizontal divider (rows with >40% single non-bg color): if found → "horizontal_balance"
  3. Return puzzle type → route to appropriate metric
- **Expected impact**: Handles both puzzle types automatically. Levels 1-2 use row metric, level 3 uses column/bar metric.

### 3. [Puzzle Logic] Total cell change count as universal trial fallback
- **Hypothesis**: If both specific metrics (row imbalance, bar height) fail to detect improvement, use the most generic metric: total cells changed. ANY button that changes >10 cells is interactive. This is a universal fallback that works for unknown puzzle types.
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
