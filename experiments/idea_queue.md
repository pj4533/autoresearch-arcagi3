# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 063): Three priorities: (1) VC33 L1-2 click optimization — quadratic scoring means fewer clicks = much better per-level scores, (2) LS20 progressive DFS with frontier navigation, (3) VC33 L3 via arc CLI visual play as stretch goal. ALL ideas are PLAY STRATEGY changes to play_strategy.md, NOT code changes.**

---

### 1. [Action Efficiency] VC33 L1-2: predict button direction from initial frame symmetry
- **Hypothesis**: The trial-and-lock approach uses 1 trial click per button before locking the best. For L1 (2 buttons, baseline 6), this wastes 1 click. If the executor can determine the correct button from the initial frame (the side with LESS green needs the opposite button), it saves a trial click. With quadratic scoring, going from 7 clicks to 6 = score jump from 73% to 100%.
- **Strategy change**: Add to VC33 strategy: "On level start, compare green fill in upper vs lower regions. The region with LESS green needs to grow → click the button that grows it. Skip trial-and-lock when the imbalance direction is visually obvious."
- **Target game**: vc33 L1-2
- **Expected impact**: Save 1 click per level. L1: 6→5 clicks (100% score). L2: 14→13 clicks (100% score).

### 2. [Action Efficiency] VC33 L1-2: compute exact click count from gap measurement
- **Hypothesis**: After identifying the correct button (via trial or visual), the agent currently clicks until the score improves (plateau detection). Instead, measure the exact gap (green cell count difference between regions), divide by cells-changed-per-click, and execute exactly that many clicks. No intermediate state checks needed.
- **Strategy change**: Add to VC33 strategy: "After the first click, measure how many cells changed. Divide remaining gap by cells-per-click to get exact count. Click that many times without checking. This eliminates plateau detection overhead and stale-step waste."
- **Target game**: vc33 L1-2
- **Expected impact**: Reduce total clicks by eliminating the 3 stale steps that trigger re-trial. Could save 2-4 clicks per level.

### 3. [Navigation] LS20: progressive DFS with frontier-first navigation across deaths
- **Hypothesis**: Each death reveals part of the maze. If the state graph persists across deaths, the agent builds a cumulative map. After respawn, it should navigate the known-good path directly (70% of action budget) then explore new territory (30%). This maximizes information gain per life.
- **Strategy change**: Add to LS20 strategy: "Death is progress, not failure. Each attempt teaches you about the maze. After respawn: (1) immediately navigate through known-safe path to the frontier of explored territory, (2) explore 1-2 new moves, (3) if you die, you've extended the map. After 3-5 deaths, the accumulated map should contain the full path."
- **Target game**: ls20
- **Expected impact**: Systematic maze exploration within health budget. Should find modifier + goal path within 5-10 deaths.

### 4. [Navigation] LS20: death-state recording to avoid lethal transitions
- **Hypothesis**: Some actions at certain states cause instant death (traps). Recording "action X at state Y = death" prevents repeating lethal moves. The agent already builds a state graph — adding "death edges" gives free information.
- **Strategy change**: Add to LS20 strategy: "When you die, record the last action and state as LETHAL. Never repeat that action at that state. This eliminates recurring deaths at the same trap."
- **Target game**: ls20
- **Expected impact**: Extends effective action budget by avoiding repeat trap deaths.

### 5. [Hypothesis Testing] VC33 L3: visual single-button investigation via arc CLI
- **Hypothesis**: Previous programmatic attempts failed because btn[0] (PPS-UP) is unreliable due to sprite overlap. The executor with vision can click buttons one at a time, SEE the exact visual effect, and build a complete button→effect map. Vision bypasses the sprite-overlap coordinate issue.
- **Strategy change**: Add to VC33 L3 strategy: "Play L3 manually via arc CLI after auto-solving L1-2. For each of the 8 buttons: (1) `arc state --image` to see current state, (2) click ONE button, (3) `arc state --image` to see what changed, (4) document: which bar grew/shrank, by how much. Build complete map before attempting solution. The colored markers (yellow=11, purple=14, light-purple=15) show target heights."
- **Target game**: vc33 L3
- **Expected impact**: Visual investigation should identify all button effects including the elusive PPS-UP button.

### 6. [Visual Analysis] LS20: detect and navigate toward colored sprites
- **Hypothesis**: The modifier (rotation changer) and goal have distinctive visual appearances. If the executor can spot them in the frame, it can navigate directly toward them instead of blind exploration. The modifier is at (19,30), goal at (34,10) — both potentially visible within the 20-pixel radius fog-of-war.
- **Strategy change**: Add to LS20 strategy: "Look for distinctive colored objects in the visible area. The modifier is a small colored sprite, the goal is another distinctive marker. When visible, navigate directly toward it. When not visible, explore in the general direction (LEFT+UP from start for modifier, then RIGHT+UP for goal)."
- **Target game**: ls20
- **Expected impact**: Goal-directed navigation reduces wasted exploration moves.

### 7. [Action Efficiency] General: action budget awareness and conservation
- **Hypothesis**: The quadratic scoring formula means every wasted action is extremely costly. 2x human actions = 25% score, 1.5x = 44%, 1x = 100%. The executor should track remaining actions and switch from exploration to exploitation mode when budget is low.
- **Strategy change**: Add to General strategy: "Track your action count. With quadratic scoring, every action costs more than linearly. If you've used more than 2x the human baseline without progress, STOP exploring and try your best hypothesis. If you've used less than 1.5x, you're on track."
- **Target game**: all
- **Expected impact**: Prevents over-exploration that wastes action budget.

### 8. [Visual Analysis] VC33: Visualization-of-Thought for spatial reasoning
- **Hypothesis**: Research shows "Visualization-of-Thought" prompting (mentally visualize intermediate states) improves spatial reasoning accuracy by 27%. For VC33 puzzles, the executor should explicitly describe the current visual state and predict the visual result of each click before executing.
- **Strategy change**: Add to VC33 strategy: "Before clicking, visualize the expected result: 'If I click this button, the green region should grow by ~X pixels in this direction.' After clicking, compare actual vs expected. If different, revise your mental model before the next click."
- **Target game**: vc33
- **Expected impact**: Better click selection through predictive reasoning, fewer wasted clicks.

### 9. [Level Progression] VC33: preserve strategy knowledge across levels
- **Hypothesis**: Levels 1-2 both use balance mechanics with green fill. Level 3 is a bar chart. Levels 4-7 may reuse or vary these mechanics. When transitioning levels, the executor should note what mechanic was used and look for similarities in the new level.
- **Strategy change**: Add to VC33 strategy: "After solving a level, note the mechanic: 'L1 = two-button balance, L2 = four-button balance with cycling.' On the new level, check if it looks similar (same button layout, same fill colors). If so, apply the same approach. If different, investigate before acting."
- **Target game**: vc33
- **Expected impact**: Faster level starts by transferring knowledge.

### 10. [Puzzle Identification] VC33 L3: bar chart equalization as left-to-right sweep
- **Hypothesis**: Research shows adjacent-transfer equalization puzzles are optimally solved by a left-to-right sweep: equalize each adjacent pair sequentially. VC33 L3 has 5 bars connected in a chain with buttons that transfer between adjacent bars. A single left-to-right pass should solve it.
- **Strategy change**: Add to VC33 L3 strategy: "L3 is a bar equalization puzzle with adjacent transfers. Optimal approach: process bars left-to-right. For each adjacent pair, click the button that transfers from the taller bar to the shorter until they match. This minimizes total clicks."
- **Target game**: vc33 L3
- **Expected impact**: Provides a concrete algorithm for the executor to follow on L3.

### 11. [Navigation] LS20: use Chain-of-Symbol spatial descriptions
- **Hypothesis**: Research shows Chain-of-Symbol prompting (using grid coordinates like "R3C5" instead of natural language) improves spatial reasoning accuracy by up to 60%. For LS20 maze navigation, the executor should describe positions symbolically.
- **Strategy change**: Add to LS20 strategy: "When analyzing the game frame, describe positions using grid coordinates: 'Player at (32,32), green path extends to (48,32), wall at (32,16).' This precision prevents navigation errors from vague spatial descriptions."
- **Target game**: ls20
- **Expected impact**: More accurate spatial reasoning and navigation decisions.

### 12. [Hypothesis Testing] General: periodic context summarization every 10 actions
- **Hypothesis**: Research on LLM game-playing shows that summarizing context every ~10 actions prevents repetitive behavior and maintains long-horizon planning. The executor should periodically review: what's been learned, what's changed, what to try next.
- **Strategy change**: Add to General strategy: "Every 10 actions, pause and summarize: (1) What have I learned about this game/level? (2) What's changed since I started? (3) What's my current hypothesis? (4) What should I try next? This prevents getting stuck in loops."
- **Target game**: all
- **Expected impact**: Reduces repetitive behavior and maintains strategic focus.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-027**: vc33 L3 bar chart — 6 exps, scoring condition found (markers).
- **Stategraph 028-045**: ls20 navigation — DFS solved (34-46 steps). Start position confirmed (39,45). State matching is blocker. Center hashing helps.
- **Stategraph 046-047**: ls20 confirmed (39,45), vc33 L3 decoded as chain-of-bars.
- **Stategraph 048-062**: vc33 L3 — 14 experiments. Phase 1-2 work (ChX/VAJ reach targets). Phase 3 (PPS) BLOCKED: btn[0] at game(6,50) overlaps with fCG rDn bar, get_sprite_at returns wrong sprite ~86% of time.
- **Stategraph 063 (IMPROVED)**: Center hashing permanent. LS20 NOT_FINISHED with 2000 actions (better exploration). vc33 no regression.
- **Executor 064**: VC33 L1-2 manual play via arc CLI. L1 solved in 6 actions, L2 in 17. L3 still blocked by PPS button. Same 2 levels, no improvement.
- **Explorer 001-030**: All score 0.
- **KEY INSIGHTS**: Coordinate mapping is display=game+6 (not scaling). Scoring is quadratic (human/agent)^2. VC33 grid sizes: L1-2=32, L3=52, L4-6=64, L7=48. Click coordinates = display grid coordinates (confirmed in exp 064).
