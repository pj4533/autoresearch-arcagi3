# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 064): SCORING IS LEVEL-WEIGHTED — level l gets weight l, denominator n*(n+1)/2. For 7-level vc33, L1-2 = 3/28 (10.7%) of max score. SOLVING NEW LEVELS >> optimizing solved levels. Exp 064 CONFIRMED: PPS button broken even with vision. Priority: (1) LS20 L1 — persistent map + maze solving, (2) VC33 L3 — need completely new approach since PPS is unfixable, (3) VC33 L4+ if L3 can be bypassed. ALL ideas are PLAY STRATEGY changes, NOT code changes.**

---

### 1. [Navigation] LS20: persistent map building across deaths (lives 1-2 = explore, life 3 = execute)
- **Hypothesis**: The maze doesn't change between deaths. Each death reveals partial map information. Use lives 1-2 purely for mapping and life 3 to execute the known solution path. Exp 040-041 proved maze IS navigable (DFS reaches 34-46 steps). Exp 064 confirms blind moves don't work — need structured exploration.
- **Strategy change**: Add to LS20 strategy: "Build a mental map across deaths. After each move, note: did the move succeed (frame changed) or fail (wall)? After death, you respawn at start but REMEMBER the map. Life 1: explore LEFT+UP toward modifier at (19,30). Life 2: follow known-safe path to frontier, explore further. Life 3: execute the complete path — start (39,45) → modifier (19,30) → goal (34,10)."
- **Target game**: ls20
- **Expected impact**: Should solve L1 within 3 lives (~54 total moves). L1 baseline=29. Even with exploration overhead, achievable.

### 2. [Navigation] LS20: frontier-first navigation after respawn
- **Hypothesis**: DFS wastes moves backtracking through already-explored territory. After respawn, navigate directly through mental map to the frontier, then explore new corridors. Budget: 70% of moves to reach frontier, 30% to explore.
- **Strategy change**: Add to LS20 strategy: "After respawn, DON'T re-explore known territory. Navigate directly through your mental map to the furthest explored point. THEN explore new corridors. This maximizes new territory discovered per life."
- **Target game**: ls20
- **Expected impact**: 2-3x more efficient exploration per life.

### 3. [Puzzle Identification] VC33 L3: bypass PPS button — find alternative mechanics
- **Hypothesis**: 16 experiments confirmed btn[0] (PPS-UP) is broken due to sprite overlap. Exp 064 confirmed it's broken even with vision. Instead of trying to fix btn[0], look for ALTERNATIVE mechanics: (a) maybe clicking the bar itself moves PPS, (b) maybe there's a reset/undo button, (c) maybe the decorations can be clicked directly, (d) maybe clicking at different y-values near btn[0] triggers a different sprite. The game has 75 lives — there's room to experiment.
- **Strategy change**: Add to VC33 L3 strategy: "btn[0] at x≈12 is confirmed broken. DON'T keep trying it. Instead, systematically explore: click at 10 different positions across the screen (top, middle, sides, near decorations, near bars). Look for ANY click that moves PPS (decoration 14). Try clicking PPS itself, clicking the bar under PPS, clicking empty space near PPS."
- **Target game**: vc33 L3
- **Expected impact**: May discover an alternative way to move PPS that doesn't involve the broken btn[0].

### 4. [Navigation] LS20: death-state recording to avoid lethal transitions
- **Hypothesis**: Some maze positions cause instant death (traps). Recording which moves at which positions killed the agent prevents repeating lethal errors.
- **Strategy change**: Add to LS20 strategy: "When you die, note the exact last action and visual state. NEVER repeat that action in that situation. Death teaches you where traps are."
- **Target game**: ls20
- **Expected impact**: Eliminates repeat trap deaths.

### 5. [Visual Analysis] LS20: detect modifier and goal sprites visually
- **Hypothesis**: The modifier and goal have distinctive appearances. The executor using arc CLI with `--image` can spot them within the fog-of-war circle and navigate toward them. Player starts at (39,45), modifier is LEFT+UP at (19,30).
- **Strategy change**: Add to LS20 strategy: "Watch for distinctive colored objects in the visible circle. The modifier and goal have unique colors/shapes different from walls and floor. When you spot one, navigate DIRECTLY toward it. Bias exploration LEFT+UP from start (that's where the modifier is)."
- **Target game**: ls20
- **Expected impact**: Goal-directed navigation reduces wasted moves by ~50%.

### 6. [Navigation] LS20: wall-following (left-hand rule) for systematic coverage
- **Hypothesis**: The left-hand rule guarantees traversal of every reachable cell in a simply-connected maze. Prevents the oscillation problem seen in exp 033-034.
- **Strategy change**: Add to LS20 strategy: "Use left-hand wall following as exploration strategy: always try to turn left from your heading. If blocked, go straight. If blocked, turn right. If all blocked, reverse. This systematically covers all corridors."
- **Target game**: ls20
- **Expected impact**: Prevents oscillation while guaranteeing complete coverage.

### 7. [Puzzle Identification] VC33 L3: left-to-right sweep after finding PPS alternative
- **Hypothesis**: Adjacent-transfer equalization puzzles are optimally solved by left-to-right sweep. If idea #3 finds a PPS alternative, the sweep algorithm provides the optimal click sequence.
- **Strategy change**: Add to VC33 L3 strategy: "Once ALL buttons are mapped: process bar pairs left-to-right. For each pair, transfer from taller to shorter until markers align. This is provably optimal for adjacent-transfer puzzles."
- **Target game**: vc33 L3
- **Expected impact**: Minimum-click solution once all buttons work.

### 8. [Action Efficiency] General: RHAE-aware action budgeting
- **Hypothesis**: RHAE = (human/agent)^2, per-game weighted by level index. Human baselines: vc33=[6,13,31,59,92,24,82], ls20=[29,41,172,49,53,62,82]. The executor should track actions vs baseline and commit to a plan before exceeding 1.5x.
- **Strategy change**: Add to General strategy: "Know the baselines. At 1.5x baseline, STOP exploring and commit. At 2x you're at 25% score. At 3x you're at 11%. Every action costs quadratically. Track your count."
- **Target game**: all
- **Expected impact**: Prevents over-exploration on solvable levels.

### 9. [Level Progression] VC33 L4+: investigate whether L3 can be survived/bypassed
- **Hypothesis**: If L3 can't be solved, can the agent survive it (NOT_FINISHED instead of GAME_OVER) and reach L4? With 75 lives on L3, the agent just needs to avoid clicking until actions run out. L4 weight = 4/28, L5 = 5/28 — solving them without L3 still adds significant score.
- **Strategy change**: Add to VC33 strategy: "If L3 can't be solved, DON'T waste lives clicking random buttons. Instead: do nothing (or click known-safe positions) to preserve lives. If the game allows progressing to L4 after max actions, investigate L4's mechanics."
- **Target game**: vc33 L3-4
- **Expected impact**: Unlocks access to L4+ if L3 is skippable.

### 10. [Visual Analysis] VC33: Visualization-of-Thought for click prediction
- **Hypothesis**: Predicting click outcomes before executing reduces wasted clicks. "If I click this button, bar X should grow by ~2px" → verify after → revise model if wrong.
- **Strategy change**: Add to VC33 strategy: "Before clicking, predict the visual result. After clicking, compare. If wrong, revise your model before next click."
- **Target game**: vc33
- **Expected impact**: Fewer wasted clicks through predictive reasoning.

### 11. [Action Efficiency] VC33 L2: optimize cycling pattern (17→13 actions)
- **Hypothesis**: Exp 064 solved L2 in 17 actions (baseline 13). The cycling pattern was B×5, D×5, B×3, D×2 = 15 productive + 2 trial = 17. Optimizing: if the executor can predict cycling from the first trial, it could skip 2-4 exploration clicks.
- **Strategy change**: Add to VC33 L2 strategy: "L2 needs button cycling (B then D then B again). After first trial of all 4 buttons, immediately start with the best button. When it plateaus (no change after 2 clicks), switch to the other effective button. Don't re-trial — just alternate."
- **Target game**: vc33 L2
- **Expected impact**: L2: 17→13-14 actions. Small RHAE impact (weight 2/28).

### 12. [Hypothesis Testing] General: periodic context summarization every 10 actions
- **Hypothesis**: LLM game-playing research shows summarizing every ~10 actions prevents loops.
- **Strategy change**: Add to General strategy: "Every 10 actions, summarize: (1) What learned? (2) What changed? (3) Current hypothesis? (4) Next plan? Prevents repetitive behavior."
- **Target game**: all
- **Expected impact**: Reduces loops in arc CLI play.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-027**: vc33 L3 bar chart — 6 exps, scoring condition found (markers).
- **Stategraph 028-045**: ls20 navigation — DFS solved (34-46 steps). Start position confirmed (39,45). Center hashing helps.
- **Stategraph 046-047**: ls20 confirmed (39,45), vc33 L3 decoded as chain-of-bars.
- **Stategraph 048-062**: vc33 L3 — 14 experiments. PPS button BLOCKED by sprite overlap.
- **Stategraph 063 (IMPROVED)**: Center hashing permanent.
- **Executor 064**: VC33 L1-2 manual play via arc CLI. L1=6 actions (baseline!), L2=17. L3 PPS still broken with vision. ls20=40 blind moves, 0 score.
- **Executor 065**: VC33 predict button + exact clicks. L1 in 3 (half human baseline!), L2 in 14. Score still 0.6667 — local scoring is levels-based not efficiency-based.
- **Explorer 001-030**: All score 0.
- **KEY INSIGHTS**: RHAE scoring = (human/agent)^2, per-game WEIGHTED by level index (l/sum(1..n)). VC33 L1-2 combined weight = 3/28 = 10.7%. Solving L3 (wt 3) nearly doubles game score. LS20 baselines: [29,41,172,49,53,62,82]. Click coords = display grid coords.
