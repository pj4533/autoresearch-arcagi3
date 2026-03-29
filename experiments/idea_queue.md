# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post BREAKTHROUGH exp 019): First non-zero score! avg=0.3333, vc33=1.0. Balance puzzle detection solved vc33 level 1. Level 2 has different layout → GAME_OVER. Priority: (1) generalize balance detection for level 2+, (2) investigate ls20 visually, (3) improve action efficiency. The hybrid approach (Claude Code reasoning + programmatic execution) works!**

---

### 1. [Puzzle Logic] Empirical button mapping for level 2 — click each, measure effect
- **Hypothesis**: Exp 020 found level 2 has 4 buttons and different green orientation (green_R, bounds 52/12). The detection found the buttons but selected the WRONG one. Instead of guessing which button to click, try each of the 4 buttons ONCE and measure which one moves the boundaries in the convergent direction. Then lock that button. This costs only 4 lives to determine the correct button — much better than guessing wrong and wasting 50.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. When balance puzzle is detected with >2 buttons: enter "calibration" phase
  2. Click each button once, recording {boundary_before, boundary_after} for each
  3. Select the button that moved boundaries CLOSER to each other (convergent)
  4. Lock that button and click repeatedly until score increases
  5. This generalizes to ANY number of buttons — always try all, pick the convergent one
  6. For 2-button puzzles (level 1), this also works but costs 2 extra clicks
- **Expected impact**: Solves level 2 by empirically determining the correct button. Generalizes to any button count. Cost: N extra clicks (one per button) for calibration.

### 2. [Puzzle Logic] Handle green_R orientation — boundary measurement goes both ways
- **Hypothesis**: Level 1 has green growing from the LEFT, level 2 has green growing from the RIGHT. The current boundary detection scans right-to-left looking for green. For green_R levels, it needs to also scan left-to-right. Auto-detecting the orientation means measuring from both sides and using the correct one.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_detect_balance_puzzle()`:
  1. Scan for green boundary from RIGHT side (current) → `boundary_R`
  2. Also scan from LEFT side → `boundary_L`
  3. Use whichever gives a meaningful measurement (boundary > 0)
  4. The convergent direction depends on orientation: green_L wants boundaries moving right, green_R wants boundaries moving left
- **Expected impact**: Handles both orientations → solves both level 1 and level 2.

### 3. [Puzzle Logic] Investigate level 2 visually — see what the 4-button layout looks like
- **Hypothesis**: The executor's exp 020 logs say "4 buttons, green_R, bounds 52/12" but the visual structure may reveal more. Seeing level 2 visually would clarify: where are the 4 buttons relative to the divider? Are they in pairs (2 upper, 2 lower)? Are some buttons redundant? What do the boundaries actually look like?
- **Files to modify**: None initially — investigation
- **Changes**: Use arc CLI to reach level 2:
  ```bash
  arc start vc33 --max-actions 100
  # Solve level 1 (click correct button ~6 times)
  arc state --image    # See level 2 layout
  # Click each of the 4 buttons and observe
  arc end
  ```
- **Expected impact**: Visual understanding of level 2 → targeted fix for button selection.

### 4. [Puzzle Logic] Add fallback: if balance detection fails, try each color-9 object once
- **Hypothesis**: When `_detect_balance_puzzle()` returns None (can't detect the pattern), the agent falls back to generic click exploration which wastes lives. A better fallback: click each color-9 object exactly once and observe effects. Then re-attempt balance detection in the new state.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_choose_action()`, when balance_mode is False and it's a click-only game: find all color-9 connected components, click each center once (ordered by size, smallest first). After each click, if >50 cells changed, re-run `_detect_balance_puzzle()`.
- **Expected impact**: Smart fallback that costs only N clicks (one per button candidate) then re-detects.

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
