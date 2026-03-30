# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 078): Stategraph ran 10000 actions on LS20 but ALL were move_up! ROOT CAUSE: health bar ticks 2 cells per action INSIDE the center hash region → every state looks "new" → DFS never backtracks. FIX: exclude health bar pixels from the hash. This is the ONLY remaining blocker — once the hash is fixed, the DFS will explore properly. ALL ideas are PLAY STRATEGY changes. The hash fix is a DIAGNOSTIC finding that the executor implements.**

---

### 1. [Navigation] LS20: fix stategraph hash to exclude health bar pixels, then re-run 10000 actions
- **DIAGNOSIS (exp 078)**: Stategraph ran 10000 actions but ALL were ACTION1 (move_up). The DFS never tried other directions because the center 20×20 hash includes the health bar, which changes 2 cells on EVERY action. The DFS sees "new state" every time and never backtracks to try ACTION2/3/4.
- **THE FIX**: The hash must exclude the health bar pixels. From exp 069: health tick = exactly 2 cells changed. These 2 cells are within the 20×20 center region. Options:
  1. **Mask the 2 health cells**: Identify which 2 cells change on health ticks and exclude them from the hash
  2. **Use a smaller center region**: Hash 16×16 or 12×12 center to avoid the health bar area
  3. **Hash only non-status-bar rows**: The health bar is likely in the top rows — exclude rows 0-3 of the center region
  4. **Use cell-change threshold for state comparison**: Only count states as "new" if >10 cells changed (filters out 2-cell health ticks)
- **AFTER FIX**: Re-run `uv run python -m arcagi3.runner --agent stategraph --game_id ls20 --max_actions 10000 --offline`. The DFS should now properly explore all 4 directions at each state.
- **Target game**: ls20
- **Expected impact**: Proper DFS exploration → finds modifier→goal path → score 0.6667→1.0.

### 2. [Navigation] LS20: if hash fix + 10000 fails, try 50000 actions
- **Hypothesis**: If proper hashing with 10000 actions isn't enough, the maze state space is very large. Try 50000 (~10 min).
- **Target game**: ls20

### 3. [Navigation] LS20: investigate which 2 cells are the health bar
- **Hypothesis**: The health bar changes exactly 2 cells per action (from exp 069's wall detection: 2 cells = blocked = health tick only). To fix the hash, need to identify WHERE these 2 cells are in the 20×20 center region. The executor can check: run 2 consecutive `arc state` commands (text grid), diff them, find the 2 changed cells. Those are the health bar positions to mask.
- **Strategy change**: "To diagnose: `arc start ls20 --max-actions 5`. Do `arc state` → `arc action move_up` → `arc state`. Diff the two grids. The 2 changed cells = health bar. These need to be excluded from the stategraph's hash."
- **Target game**: ls20
- **Expected impact**: Identifies exact health bar position for hash masking.

### 4. [Navigation] LS20: alternative — use cell-change THRESHOLD instead of exact hash
- **Hypothesis**: Instead of fixing the hash to exclude specific pixels, use a cell-change threshold for "same state" detection. If <10 cells changed → same state (don't explore). If 10+ cells changed → new state (explore). This filters out the 2-cell health ticks AND wall-hit ticks without needing to know which cells are the health bar.
- **Strategy change**: "Alternative to hash masking: modify state comparison to use a change threshold. States differing by <10 cells = same state. This filters health ticks (2 cells) and wall hits (2 cells) while detecting real moves (52+ cells)."
- **Target game**: ls20
- **Expected impact**: Simpler fix — no need to identify exact health bar cells.

### 5. [Navigation] LS20: after solving L1, optimize path for RHAE
- **Hypothesis**: DFS solution path will be long. Optimize by replaying minimum path.
- **Target game**: ls20

### 6. [Level Progression] VC33 L3: don't click, conserve lives
- **Hypothesis**: L3 unsolvable. Stop clicking.
- **Target game**: vc33 L3

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-070**: vc33 L3 — 20 experiments. CLOSED (unsolvable).
- **Stategraph 063 (IMPROVED)**: Center hashing permanent. LS20 NOT_FINISHED with 2000 actions.
- **Executor 064-065**: VC33 L1=3, L2=14.
- **Executor 066-077**: LS20 manual navigation — 8 experiments, all 0 score. CLOSED (3 blockers).
- **Executor 076**: VC33 optimized baseline (L1=3, L2=16, L3 skipped). Score ceiling 0.6667.
- **Executor 078**: Stategraph 10000 actions → ALL move_up! **Health bar in center hash = every state "new."** DFS never backtracks. FIX: exclude health bar from hash.

## Dead Ends (Confirmed)
- **VC33 L3**: UNSOLVABLE (87 clicks = 0 PPS movement)
- **LS20 via arc CLI**: 8 experiments (066-077), all 0. THREE blockers: cyclic topology, display≠game alignment, maze changes after death.
- **LS20 stategraph with current hash**: Health bar in center hash makes every state unique → DFS only does move_up (exp 078). MUST fix hash first.
- Death-replay for LS20: INVALID (maze changes after death)
- ft09, Qwen models, position waypoints, hardcoded paths: all dead ends.
