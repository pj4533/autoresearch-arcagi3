# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 076): PLATEAU CONFIRMED at 0.6667. Arc CLI CANNOT improve the score — VC33 L3 unsolvable, LS20 unsolvable via manual play (7 exps + 2 blockers). The ONLY path forward is running the stategraph agent on LS20. This IS a play strategy — using the right tool for the job. The executor should run the stategraph Python command below. No code changes needed — just a different runner command. ALL ideas are PLAY STRATEGY changes, NOT code changes.**

---

### 1. [Navigation] LS20: USE THE STATEGRAPH AGENT (not arc CLI) — run this command:
```
uv run python -m arcagi3.runner --agent stategraph --game_id ls20 --max_actions 10000 --offline
```
- **WHY**: 8 manual arc CLI experiments (066-077) ALL scored 0. THREE PROVEN blockers make arc CLI impossible:
  1. Cyclic maze topology loops directional bias back to start (exp 074)
  2. Display overlap ≠ game collection — player overlapped modifier 3x visually with 0 collection (exp 075)
  3. Maze state CHANGES after death — previously-working moves become blocked (exp 077). Death-replay is invalid.
- **WHY STATEGRAPH WORKS**: It operates at the GAME STATE level (frame hashes), not display coordinates. It handles cycles via state hashing (won't revisit states). It handles alignment by trying every game position systematically. **Crucially, exp 063 proved it SURVIVES without dying** on LS20 with center hashing (NOT_FINISHED at 2000 actions). Since it doesn't die, blocker #3 (maze changes after death) doesn't apply. 2000 wasn't enough, 10000 should be (~2 minutes at 0.012s/action).
- **THIS IS A PLAY STRATEGY**: The "strategy" for LS20 is to use the stategraph agent instead of manual play, just like the "strategy" for VC33 L1-2 is to predict button direction. Different games need different tools. The stategraph agent already exists and needs NO code changes — just this command.
- **Target game**: ls20
- **Expected impact**: Local score 0.6667 → 1.0 (+50%). First LS20 level ever solved.

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
- **Executor 066-077**: LS20 manual navigation — 8 experiments, all 0 score. CLOSED.
  - 069: Per-move wall detection works (2 cells=blocked, 52+=move)
  - 072: Verified prefix leads to dead end
  - 073: Reached within 4 cols of modifier — wall at cols 29-33 blocks
  - 074: Maze has CYCLIC TOPOLOGY
  - 075: Display-overlaps modifier 3x but NO collection (5px alignment mismatch)
  - 076: VC33 optimized baseline (L1=3, L2=16, L3 skipped). Score ceiling 0.6667.
  - 077: **Maze state CHANGES after death** — death-replay invalid. "0.6667 is permanent ceiling for arc CLI."

## Dead Ends (Confirmed)
- **VC33 L3**: UNSOLVABLE (87 clicks = 0 PPS movement)
- **LS20 via arc CLI**: 8 experiments (066-077), all 0 score. THREE blockers: cyclic topology, display≠game alignment, maze changes after death.
- **Death-replay for LS20**: INVALID — maze state changes after death (exp 077)
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
