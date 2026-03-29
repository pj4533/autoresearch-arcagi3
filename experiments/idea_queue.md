# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post BREAKTHROUGH exp 019): First non-zero score! avg=0.3333, vc33=1.0. Balance puzzle detection solved vc33 level 1. Level 2 has different layout → GAME_OVER. Priority: (1) generalize balance detection for level 2+, (2) investigate ls20 visually, (3) improve action efficiency. The hybrid approach (Claude Code reasoning + programmatic execution) works!**

---

### 1. [Puzzle Logic] Investigate vc33 level 2 — what's different?
- **Hypothesis**: Exp 019 solved level 1 but level 2 has a "different layout" → GAME_OVER. The executor should visually investigate level 2 to understand how it differs. Does it have the same balance puzzle structure with different parameters? Different colors? Different orientation (vertical vs horizontal)? Different number of buttons? Understanding level 2 is the key to extending the score.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py` (after investigation)
- **Changes**: Use arc CLI to reach level 2 and inspect it:
  ```bash
  arc start vc33 --max-actions 100
  # First, solve level 1 using the known strategy
  # (click the correct button repeatedly)
  arc state --image    # See level 2 layout
  # Try different clicks and observe
  arc end
  ```
  Or: temporarily add debug logging to `_detect_balance_puzzle()` to print what it sees on level 2. Does it find the gray bar? Does it find buttons? What are the boundaries?

  Based on findings, generalize the detection to handle level 2's layout.
- **Expected impact**: If level 2 is a variation of the same puzzle (different positions/sizes), a single generalization could solve it → vc33 score jumps from level-1-only to multi-level.

### 2. [Puzzle Logic] Generalize balance detection — handle different divider colors/positions
- **Hypothesis**: The current detection hardcodes gray bar detection (color 5, >40% of row). Level 2+ may have: different divider color, different position (not horizontal), different bar width, or the divider might be a different structure entirely. Making the detection more flexible would handle variations.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Instead of looking for a specific color bar, look for ANY horizontal band of uniform non-background color that spans >30% of the row
  2. Handle dividers at any position (not just the middle)
  3. Support different boundary colors (not just green=3 vs black=0)
  4. Auto-detect the "adjustable" colors by finding which colors change when buttons are clicked
  5. Support more than 2 buttons (level 2+ might have 3 or 4)
- **Expected impact**: Handles vc33 level variations → multi-level solving.

### 3. [Puzzle Logic] Add fallback: if balance detection fails, click ALL color-9 objects once
- **Hypothesis**: When `_detect_balance_puzzle()` returns None (can't detect the pattern), the agent falls back to generic click exploration which wastes lives. A better fallback: click each color-9 object exactly once and observe effects. Since color 9 is confirmed interactive (exp 002), this at least triggers the puzzle mechanic. The agent can then decide based on which click produced the most useful change.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_choose_action()`, when balance_mode is False and it's a click-only game: find all color-9 connected components, click each center once (ordered by size, smallest first). After each click, if >50 cells changed, attempt to detect the balance pattern again.
- **Expected impact**: Smart fallback that doesn't waste lives. Triggers the puzzle mechanic and may re-enable balance detection.

### 4. [Puzzle Logic] Investigate vc33 levels 3-7 — are they all balance puzzles?
- **Hypothesis**: vc33 has 7 levels with baselines [6, 13, 31, 59, 92, 24, 82]. If ALL levels are balance puzzles (just with different parameters), the same strategy generalizes. If some levels are fundamentally different puzzle types, we need different strategies.
- **Files to modify**: Investigation first, then agent.py
- **Changes**: Run vc33 with max_actions=500 and debug logging. After solving each level, log what the new level looks like. Identify which levels are balance puzzles and which need different strategies.
- **Expected impact**: Full picture of what's needed for vc33 multi-level solving.

### 5. [Frame Analysis] Investigate ls20 visually — understand the navigation game
- **Hypothesis**: ls20 is a navigation game with latent state. Visual investigation (like what unlocked vc33) might reveal the game structure: walls, paths, player position, objectives. Understanding ls20 mechanics is prerequisite for any ls20 strategy.
- **Files to modify**: None initially — investigation
- **Changes**: Use arc CLI:
  ```bash
  arc start ls20 --max-actions 50
  arc state --image    # See the grid
  arc action move_right
  arc state --image    # What moved? Where's the player?
  arc action move_down
  arc state --image    # How does the map scroll?
  arc end
  ```
  Identify: player position, visible objects (keys? doors?), wall structure, goal indicators.
- **Expected impact**: Understanding ls20 mechanics → targeted navigation strategy.

### 6. [Life Management] VC33 health bar tracking + conservative mode
- **Hypothesis**: vc33 health bar is in row 0 (orange=remaining, yellow=depleted). When the balance detection fails on level 2 and the agent starts random clicking, it should monitor lives. When lives are low, stop clicking entirely rather than GAME_OVER.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add `_parse_health(grid)` → count orange cells in row 0. When lives < 5, return None from `_choose_action()` (or return a no-op). This preserves the level 1 score instead of losing everything to GAME_OVER.
- **Expected impact**: Preserves score from solved levels even when later levels can't be solved.

### 7. [Action Priority] Optimize level 1 clicks — reduce from N to 6
- **Hypothesis**: Level 1 baseline is 6 clicks. The agent currently clicks the locked button until score changes, but may be clicking more times than needed (every click costs a life). If we can detect when the boundaries are equal (balanced), we can stop clicking sooner.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_detect_balance_puzzle()`, after each click, re-check the boundaries. When upper_boundary ≈ lower_boundary (within 1-2 cells), stop clicking. This minimizes wasted clicks.
- **Expected impact**: Better action efficiency → higher per-level score. Fewer lives consumed on level 1 → more lives for level 2.

### 8. [Cross-Level Transfer] Remember button positions across levels
- **Hypothesis**: vc33 levels may have buttons in similar positions. Remembering where buttons were on level 1 gives a starting point for level 2 detection. Even if positions shift, the relative structure (above/below divider) may persist.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: On level transition, save `{"button_colors": [9], "button_count": 2, "divider_present": True}` to datastore. On new level, use this to seed detection with known patterns.
- **Expected impact**: Faster level 2+ detection.

### 9. [Puzzle Logic] Handle vertical dividers — rotated balance puzzles
- **Hypothesis**: Level 2+ might have vertical dividers instead of horizontal. The current detection only looks for horizontal bars. Adding vertical bar detection would handle 90-degree rotations.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After horizontal bar check fails, try vertical: scan columns for >40% uniform non-bg color. If found, measure left/right boundaries instead of upper/lower. Button positions would be left/right of the divider.
- **Expected impact**: Handles rotated puzzle layouts.

### 10. [Puzzle Logic] Multi-button balance — more than 2 buttons
- **Hypothesis**: Later levels may have 3 or 4 buttons (more complex balance puzzles). The current code only handles exactly 2. If there are more, the agent needs to identify which subset to click.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: If >2 color-9 objects found: try each one individually (click once, measure boundary change). The one that moves boundaries in the correct direction is the target. Lock that button.
- **Expected impact**: Handles more complex puzzle layouts.

### 11. [Frame Analysis] Dynamic boundary color detection
- **Hypothesis**: Level 1 uses green (3) vs black (0) boundaries. Later levels may use different colors. Instead of hardcoding green, detect which colors occupy the two regions divided by the bar.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_detect_balance_puzzle()`: scan upper region and lower region. Find the two dominant colors in each (excluding bar color). Use those as the "boundary" colors instead of hardcoded green/black.
- **Expected impact**: Handles different color schemes across levels.

### 12. [Puzzle Logic] LS20 player detection + directional strategy
- **Hypothesis**: LS20 has a player character that moves on a grid. If we can detect the player's position (likely a unique-colored small object), we can implement basic directional strategies: "move toward the nearest unexplored area" or "follow paths."
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add player detection: find the smallest uniquely-colored object that moves when movement actions are taken. Track its position across frames. Use position to decide movement direction.
- **Expected impact**: Purposeful navigation instead of random exploration.

### 13. [Puzzle Logic] VC33 convergence detection — stop when balanced
- **Hypothesis**: The balance puzzle goal is likely to make two regions equal. Detecting convergence (boundaries match) means the agent can stop clicking the current button and submit/wait. This prevents overshooting.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After each click in balance mode, recompute boundaries. If |upper - lower| <= 1, consider the puzzle solved for this level. Stop clicking.
- **Expected impact**: More precise solving, fewer wasted clicks.

### 14. [Frame Analysis] Grid structure classifier — detect puzzle type automatically
- **Hypothesis**: Different levels may be different puzzle types (balance, sorting, matching, etc.). A simple classifier that analyzes grid structure (divider presence, object count, symmetry) could route to the appropriate strategy.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add `_classify_puzzle(grid)` that returns: "balance" (divider + 2 regions), "matching" (symmetric halves), "sorting" (ordered sequence), "unknown". Route to specific strategies based on classification.
- **Expected impact**: Handles multiple puzzle types across levels.

### 15. [Life Management] GAME_OVER prevention — return no-op when stuck
- **Hypothesis**: When the agent can't detect a puzzle pattern and lives are below threshold, it should stop acting rather than consume remaining lives on random clicks. A GAME_OVER from level 2 might erase the level 1 score.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_choose_action()`: if no balance puzzle detected AND available == ["ACTION6"] AND lives < threshold → return a "safe" action (or just keep clicking the last known-good button).
- **Expected impact**: Preserves accumulated score from solved levels.

---

## Completed

- **Stategraph 001-018**: All score 0. See log. Key findings: vc33 clicks work (color 9 interactive), ft09 broken, both games have life mechanics, programmatic exploration ceiling, all 3 local models fail.
- **Stategraph 019**: **BREAKTHROUGH** avg=0.3333, vc33=1.0. Balance puzzle detection solved level 1. Level 2 different layout → GAME_OVER. Visual investigation via arc CLI was the key insight.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
