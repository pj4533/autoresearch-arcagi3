# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 025): Level 3 bars have colored markers (colors 11, 14, 15) indicating TARGET HEIGHTS. The targets are right there on the grid. The programmatic agent can detect these marker colors and use their Y positions as targets. For each bar: find the marker → compute current bar height → click button to adjust toward marker. This is solvable programmatically!**

---

### 1. [Puzzle Logic] Per-button column-diff probing — determine WHICH bar each button controls
- **Hypothesis**: Exp 026 detected markers (gaps=[3,0,3,17]) but button→bar mapping was wrong — the agent assumed left buttons control adjacent bars but "clicks may affect different bars than assumed." The fix: click each button ONCE, diff the grid PER COLUMN to find which column changed most. This gives a definitive mapping. With 4 bar pairs and 8 buttons, each pair has a left and right button. The probe determines which is which.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Save full grid snapshot before each trial click
  2. Click button[i], get new grid
  3. For each column, count changed cells: `column_changes[col] = sum(1 for r if old[r][col] != new[r][col])`
  4. The column with the MOST changes is the bar controlled by button[i]
  5. Compare the bar's boundary BEFORE and AFTER: if boundary moved UP → button increases height, if DOWN → button decreases height
  6. Store mapping: `{button_idx: (bar_col_range, direction, pixels_per_click)}`
  7. After probing all 8 buttons (8 clicks, 8 lives): compute exact clicks per button using gaps from marker detection
  8. Execute the plan: click each button the computed number of times

  **Key difference from exp 026**: Instead of assuming left-button-per-pair, MEASURE which bar each button actually affects. The per-column diff is definitive.
- **Target game**: vc33 (level 3)
- **Expected impact**: Solves level 3. Marker gaps already detected ([3,0,3,17]). With correct button→bar mapping, the agent clicks each button the right number of times. Cost: 8 probe clicks + ~23 execution clicks = ~31 total. Within 75 lives.

### 2. [Puzzle Logic] Handle bar direction — measure boundary shift per trial click
- **Hypothesis**: Each button pair has one that increases and one that decreases bar height. After column-diff probing reveals which bar a button controls, measure the DIRECTION: scan the affected bar before/after the trial click. If the topmost filled cell moved UP → button increases height. If it moved DOWN → button decreases height. Use the direction + gap to pick the correct button and click count.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: During probe phase, for the affected bar column range, find the topmost non-background row before and after. Delta_y = after - before. If delta_y < 0 (bar grew taller), this button INCREASES height. Record direction in mapping.
- **Target game**: vc33
- **Expected impact**: Correct direction selection prevents clicking the wrong button (which would move AWAY from target).

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

- **Stategraph 001-024**: See log. Highlights: vc33 levels 1-2 solved. Level 3 bar chart: buttons detected (36-296 cells changed) but bars need SPECIFIC click counts — "puzzle requires understanding target heights." Uniform clicking doesn't work.
- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 023-024**: Cell-change metric + 5-click max. Level 3 buttons found but target heights unknown.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
