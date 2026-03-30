# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 074): Executor CONFIRMS: "Manual arc CLI navigation CANNOT solve LS20. Requires algorithmic DFS with state hashing." Maze has CYCLIC TOPOLOGY — directional bias loops back to start. Modifier sits INSIDE loop, unreachable manually. The stategraph agent handles cycles naturally (state hashing prevents revisiting). Run stategraph with 10000+ actions. ALL ideas are PLAY STRATEGY changes, NOT code changes.**

---

### 1. [Navigation] LS20: run stategraph agent with --max_actions 10000
- **Hypothesis**: 6 manual experiments (066-074) all failed. Executor confirms maze requires DFS with state hashing — EXACTLY what the stategraph agent does. Exp 063 proved center hashing keeps agent alive (NOT_FINISHED with 2000 actions). 2000 wasn't enough, but the maze's cyclic topology means the DFS will avoid loops and explore deeply. 10000 actions at 0.012s/action = ~2 minutes.
- **Strategy change**: Update LS20 strategy: "Do NOT play LS20 via arc CLI. Run: `uv run python -m arcagi3.runner --agent stategraph --game_id ls20 --max_actions 10000 --offline`. The DFS with center hashing handles the cyclic maze topology that defeats manual navigation. If 10000 isn't enough, try 50000 (~10 min)."
- **Target game**: ls20
- **Expected impact**: DFS systematically explores all corridors including the one inside the cycle that leads to the modifier. Local score: 0.6667 → 1.0.

### 2. [Navigation] LS20: if 10000 fails, try 50000 actions
- **Hypothesis**: If 10000 actions isn't enough, the reachable state space is very large or center hashing collapses distinct states. 50000 actions at 0.012s/action = ~10 minutes. Should exhaustively cover any finite maze.
- **Strategy change**: "If 10000 fails: `--max_actions 50000`. Takes ~10 minutes."
- **Target game**: ls20
- **Expected impact**: Near-exhaustive exploration.

### 3. [Navigation] LS20: if 50000 fails, investigate center hash collisions
- **Hypothesis**: If even 50000 actions doesn't find the solution, center hashing (20×20) might be collapsing distinct positions. In repetitive maze corridors, two different positions can have identical center views. The DFS would skip the second position. Fix: increase hash region to 30×30 or hash the full grid minus status bars.
- **Strategy change**: "If 50000 fails: center hashing may be collapsing states. Try a larger hash region or full-grid hashing. The fog-of-war circle is radius 20 — hash the entire visible circle."
- **Target game**: ls20
- **Expected impact**: Identifies and fixes state collisions if they're the blocker.

### 4. [Navigation] LS20: after solving L1, optimize path for RHAE
- **Hypothesis**: DFS solution path will be much longer than baseline (29 actions). But once the correct state sequence is known, it can be replayed efficiently. The stategraph logs actions — analyze the log to find the minimum path.
- **Strategy change**: "After L1 solve: study the stategraph's action log. Find the shortest sub-path that visits modifier then goal. Replay that path for RHAE optimization."
- **Target game**: ls20
- **Expected impact**: RHAE optimization after initial solve.

### 5. [Level Progression] LS20: stategraph should auto-continue to L2+ after L1
- **Hypothesis**: The stategraph agent continues playing after level completion. L2-7 mazes have similar structure. The DFS approach works for any maze level. With 10000 total actions, after L1 uses ~5000, L2 gets the remaining ~5000.
- **Strategy change**: "Run with enough total actions for multiple levels. If L1 takes 5000, set --max_actions 20000 to give L2+ budget too."
- **Target game**: ls20 L2+
- **Expected impact**: Additional levels add weighted score.

### 6. [Level Progression] VC33 L3: don't click, conserve lives
- **Hypothesis**: L3 unsolvable. Stop clicking.
- **Strategy change**: "On L3, stop clicking immediately."
- **Target game**: vc33 L3
- **Expected impact**: Prevents GAME_OVER.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-070**: vc33 L3 — 20 experiments. CLOSED (unsolvable).
- **Stategraph 063 (IMPROVED)**: Center hashing permanent. LS20 NOT_FINISHED with 2000 actions.
- **Executor 064-065**: VC33 L1=3, L2=14.
- **Executor 066-075**: LS20 manual navigation — 7 experiments, all 0 score. CLOSED.
  - 069: Per-move wall detection works (2 cells=blocked, 52+=move)
  - 072: Verified prefix leads to dead end
  - 073: Reached within 4 cols of modifier — wall at cols 29-33 blocks
  - 074: Maze has CYCLIC TOPOLOGY
  - 075: **DEFINITIVE**: Player display-overlaps modifier 3x but NO collection. 5px grid doesn't align with collection trigger. Manual CLI CANNOT solve the alignment problem.

## Dead Ends (Confirmed)
- **VC33 L3**: UNSOLVABLE (87 clicks = 0 PPS movement)
- **LS20 via arc CLI**: 7 experiments (066-075), all 0 score. Maze cycles + 5px alignment mismatch. Display overlap ≠ collection. Manual play CANNOT solve LS20.
- ft09 game version broken
- All local Qwen models for reasoning
- Position-based waypoints (tracking unreliable)
- Hardcoded paths from source (collision model proprietary)

## Key Maze Knowledge (exps 069-074)
- Start: (39,45). Modifier: (19,30). Goal: (34,10).
- **Cyclic topology**: corridors form closed loop. DOWN from upper-left returns to start.
- Wall at cols 29-33 around row 32 separates modifier from adjacent corridors
- Modifier sits INSIDE the loop, unreachable by directional bias
- The stategraph DFS handles cycles via state hashing — it won't loop
