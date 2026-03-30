# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 071): Executor explicitly says "LS20 requires actual DFS with state tracking." That IS the stategraph agent. Stop manual arc CLI play for LS20 — use the stategraph with massive action budget (10000+). Exp 063 proved center hashing keeps the agent alive on LS20 (NOT_FINISHED with 2000 actions). The fix is simple: MORE ACTIONS. At 0.012s/action with no LLM, 10000 actions = ~2 minutes. ALL ideas are PLAY STRATEGY changes, NOT code changes.**

---

### 1. [Navigation] LS20: run stategraph agent with 10000 actions (not arc CLI)
- **Hypothesis**: Exp 071 concluded "requires actual DFS with state tracking, not blind navigation." The stategraph agent IS actual DFS with state tracking. Exp 063 proved center hashing keeps the agent alive on LS20 (NOT_FINISHED, no death). 2000 actions wasn't enough — the maze is large. 10000 actions at 0.012s/action = 2 minutes. The DFS will systematically explore every reachable state. When the player steps on the modifier, the player sprite rotates → new frame hash → new state → DFS continues from post-modifier state → eventually reaches goal → level complete.
- **Strategy change**: Update LS20 strategy: "For LS20, do NOT play via arc CLI. Instead, run the stategraph agent with a large budget: `uv run python -m arcagi3.runner --agent stategraph --game_id ls20 --max_actions 10000 --offline`. The DFS with center hashing will systematically explore the maze. This takes ~2 minutes. If 10000 isn't enough, try 50000 (~10 min)."
- **Target game**: ls20
- **Expected impact**: DFS should eventually find modifier→goal path. Even with 10000 actions, local score improves (levels solved 2→3 = score 0.6667→1.0).

### 2. [Navigation] LS20: if 10000 fails, try 50000 actions
- **Hypothesis**: If 10000 actions isn't enough, the state space is very large. 50000 actions at 0.012s/action = 10 minutes. This should exhaustively cover any reachable maze.
- **Strategy change**: "If 10000 fails: `--max_actions 50000`. At 0.012s/action this takes ~10 minutes."
- **Target game**: ls20
- **Expected impact**: Near-exhaustive exploration of the state space.

### 3. [Navigation] LS20: verify center hashing quality for maze navigation
- **Hypothesis**: If huge budgets still don't solve LS20, the issue might be center hashing collapsing distinct positions. The 20×20 center region might look the same in different maze corridors, causing the DFS to think it's visited a state when it hasn't. Test: run with different hash sizes (10×10, 30×30, full grid minus status bar).
- **Strategy change**: "If 50000 actions fails: the center hash might be collapsing states. Try changing the hash region size."
- **Target game**: ls20
- **Expected impact**: Identifies whether hashing quality is the blocker.

### 4. [Navigation] LS20: after solving L1, optimize path for RHAE
- **Hypothesis**: The stategraph's DFS solution path will be much longer than the human baseline (29 actions). But once the path is known (from the state graph), the executor can analyze it and find a shorter replay. The stategraph agent checkpoints, so the solution can be studied.
- **Strategy change**: "After L1 is solved (even with 10000 actions), study the solution path. Identify the minimum-length sub-path that visits the modifier then goal. Replay just that sub-path for RHAE optimization."
- **Target game**: ls20
- **Expected impact**: Once the correct path is known, RHAE can be optimized by replaying it efficiently.

### 5. [Level Progression] LS20: multi-level data for L2-7
- **Hypothesis**: After L1, apply the same stategraph DFS to L2-7. Known data per level:
  - L2: start (29,40) → mod (49,45) → goal (14,40)
  - L3: start (9,45) → mod (49,10) → goal (54,50)
  - L4: start (54,5) → NO modifier → goal (9,5)
  - L5-7: similar patterns
- **Strategy change**: "If stategraph solves L1, it should automatically continue to L2+. The DFS approach works for any maze level."
- **Target game**: ls20 L2+
- **Expected impact**: Each additional level adds weighted score.

### 6. [Level Progression] VC33 L3: don't click, conserve lives
- **Hypothesis**: L3 is confirmed unsolvable (87 clicks = 0 PPS movement). Don't waste lives on L3.
- **Strategy change**: "On VC33 L3, stop clicking immediately. Let session end as NOT_FINISHED."
- **Target game**: vc33 L3
- **Expected impact**: Prevents GAME_OVER from random L3 clicks.

### 7. [Action Efficiency] General: RHAE-aware budgeting
- **Hypothesis**: For competition scoring, action efficiency matters. LS20 L1 baseline=29.
- **Strategy change**: "After solving a level with DFS, study the path. Minimum path = best RHAE."
- **Target game**: all
- **Expected impact**: Optimizes competition score after initial solve.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-027**: vc33 L3 bar chart — 6 exps.
- **Stategraph 028-045**: ls20 navigation — DFS solved (34-46 steps). Center hashing helps.
- **Stategraph 048-062**: vc33 L3 — 14 experiments.
- **Stategraph 063 (IMPROVED)**: Center hashing permanent. LS20 NOT_FINISHED with 2000 actions.
- **Executor 064-065**: VC33 L1=3, L2=14.
- **Executor 066-069**: LS20 per-move protocol works but manual navigation too slow.
- **Executor 070**: VC33 L3 CLOSED — unsolvable (30 positions, 0 PPS movement).
- **Executor 071**: LS20 500-action smart nav fails. **"Requires actual DFS with state tracking."**

## Dead Ends (Confirmed)
- **VC33 L3 entirely**: 87 clicks across all positions = 0 PPS movement. UNSOLVABLE.
- **LS20 via arc CLI manual play**: 3 experiments (066, 069, 071), all 0 score. Maze too complex for manual navigation. Use stategraph instead.
- Batch moves on LS20 (invisible walls)
- All local Qwen models for reasoning
- ft09 game version broken
- Position-based waypoints (tracking unreliable)
- Hardcoded paths from source (collision model proprietary)
