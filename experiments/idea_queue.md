# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 027): vc33 level 3 scoring condition unknown after 6 experiments (022-027). Markers detected, buttons probed, targeted clicking tried — still no score. Pivoting to ls20. The arc CLI visual approach should reveal ls20's navigation mechanics. Also: vc33 level 3 may need the executor to visually inspect it via `arc state --image` to understand what the ACTUAL goal is.**

---

### 1. [Navigation Strategy] Investigate ls20 visually — identify player, goals, mechanics
- **Hypothesis**: The visual investigation approach unlocked vc33 (exp 019). Apply the same approach to ls20. Claude Code can SEE the grid via `arc state --image` and identify: the player character, walls/obstacles, health indicator, goal objects, interactive elements. This understanding is prerequisite for any ls20 strategy. With 29 baseline actions for level 1, even a partially correct strategy could score.
- **Files to modify**: None initially — investigation. Then `src/arcagi3/stategraph_agent/agent.py` based on findings.
- **Changes**: Use arc CLI interactively:
  ```bash
  arc start ls20 --max-actions 50
  arc state --image    # See the initial grid — identify player, objects, walls
  arc action move_right
  arc state --image    # What moved? Where did the player go?
  arc action move_down
  arc state --image    # How does the grid respond to movement?
  arc action perform
  arc state --image    # Does perform do anything at the current location?
  arc end
  ```
  Key questions to answer: (1) Where is the player? (2) What does the goal look like? (3) How does health drain work visually? (4) Are there collectible objects? (5) What does `perform` do?
- **Target game**: ls20
- **Expected impact**: Understanding ls20 mechanics → targeted strategy. Even level 1 score would increase avg from 0.6667.

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

### 3. [Navigation Strategy] LS20 health-aware exploration — monitor and conserve
- **Hypothesis**: ls20 has health drain that kills the agent. The health indicator is likely visible (colored bar). The agent should monitor health and switch to conservative mode when health is low — only traverse known-safe paths, don't explore new areas.
- **Strategy change / Files**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add health detection (scan for color-7 orange bar in status area). When health < 30%, stop exploring new states and only use known transitions.
- **Target game**: ls20
- **Expected impact**: Prevents GAME_OVER, preserves more actions for purposeful navigation.

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
