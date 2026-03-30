# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 078 IMPASSE): BLOCKED ON CODE CHANGE. The stategraph hash window (rows 22-41) captures only fog-of-war; player is in rows 45-55. Fix = shift hash to rows 35-60. This is a 2-line change but program.md prohibits .py modifications. AWAITING HUMAN INTERVENTION to either make the fix or update program.md rules. All play-strategy-only approaches are EXHAUSTED (15 experiments, 0 improvement since exp 021).**

---

### 1. [Navigation] LS20: fix stategraph hash region to rows 35-60, then re-run 10000 actions
- **DIAGNOSIS (exp 078, grid-diff verified)**: Center 20×20 hash = rows 22-41 = pure fog-of-war (all gray 5s). Player moves in rows 45-55 (BELOW the hash region). Health bar at row 61 col 13 (also outside). Hash is IDENTICAL for all states → DFS always picks ACTION1. 10000 × move_up.
- **THE FIX**: Hash rows 35-60 instead of center 20×20. This captures the player+maze area. Alternatively: hash full grid minus rows 0-7 and 61-63 (status bars). Key data from grid diff:
  - Rows 22-41: fog-of-war (gray 5s) — CONSTANT, useless for hashing
  - Rows 45-55: player + maze content — CHANGES with movement
  - Row 61, col 13: health bar tick — exclude
- **AFTER FIX**: Re-run `uv run python -m arcagi3.runner --agent stategraph --game_id ls20 --max_actions 10000 --offline`. With proper state distinction, the DFS will explore all 4 directions at each state.
- **Target game**: ls20
- **Expected impact**: Proper DFS → finds modifier→goal path → score 0.6667→1.0.

### 2. [Navigation] LS20: if hash fix + 10000 fails, try 50000 actions
- **Hypothesis**: If proper hashing with 10000 actions isn't enough, try 50000 (~10 min).
- **Target game**: ls20

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
