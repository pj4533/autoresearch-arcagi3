# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 073): VERY CLOSE to modifier! Player at (24,35), modifier at (20,32) — 4 cols apart but wall at cols 29-33 blocks. Need to find the corridor connecting cols 34+ to cols 14-28. Three approaches: (1) probe the wall from different rows to find a gap, (2) approach modifier from BELOW by going DOWN first from start, (3) stategraph DFS with 10000 actions as fallback. ALL ideas are PLAY STRATEGY changes, NOT code changes.**

---

### 1. [Navigation] LS20: probe the wall at cols 29-33 from different rows
- **Hypothesis**: The wall at cols 29-33 (blocking modifier access) likely has a GAP at certain rows. Exp 073 hit the wall at row 32. Try rows 25, 28, 30, 34, 37, 40 — the gap might be above OR below. Mazes always have connecting corridors; the gap just needs to be found.
- **Strategy change**: Add to LS20 strategy: "From position near (24,35): go DOWN or UP along the wall (moving parallel to cols 29-33) and try LEFT at each row. The wall has a gap somewhere — keep probing. Try at least 5 different rows above and below row 32. Each probe: move to new row, try LEFT. If LEFT works (52+ cells change), you're through the wall."
- **Target game**: ls20
- **Expected impact**: Finding the gap puts the player on the modifier's side of the wall. Then ~2-3 more moves reach the modifier.

### 2. [Navigation] LS20: approach modifier from BELOW (start with DOWN, not UP)
- **Hypothesis**: Exps 069-073 all went UP first and hit dead ends or the wall from above. What if the connecting corridor is BELOW the starting position? From start (39,45), go DOWN first, then LEFT past the wall's bottom edge, then UP to modifier (19,30). U-shaped path around the wall.
- **Strategy change**: Add to LS20 strategy: "If probing the wall from above fails: try approaching from below. From start, go DOWN×3-5 (to rows 55-60+), then LEFT past cols 29-33, then UP toward modifier at row 30. The wall might not extend all the way down."
- **Target game**: ls20
- **Expected impact**: Different approach angle may bypass the wall entirely.

### 3. [Navigation] LS20: systematic wall-edge tracing
- **Hypothesis**: Once at the wall, trace along it (UP or DOWN) until finding the gap. This is guaranteed to find the corridor — just follow the wall edge.
- **Strategy change**: Add to LS20 strategy: "When you hit the wall at cols 29-33: don't backtrack. Instead, move ALONG the wall (UP or DOWN) while periodically trying LEFT. You're tracing the wall's edge. Eventually you'll find the corridor that passes through. This is a wall-following strategy applied to a specific wall."
- **Target game**: ls20
- **Expected impact**: Systematic wall tracing guarantees finding the gap.

### 4. [Navigation] LS20: stategraph DFS with 10000 actions (parallel approach)
- **Hypothesis**: While manual play has made great progress (within 4 cols of modifier), the stategraph DFS can explore systematically. Run `--max_actions 10000` as a parallel test. If it finds the path, the manual approach can be informed by the solution.
- **Strategy change**: "As a parallel test: `uv run python -m arcagi3.runner --agent stategraph --game_id ls20 --max_actions 10000 --offline`. The DFS will systematically try every corridor including the gap around the wall."
- **Target game**: ls20
- **Expected impact**: DFS should find the connecting corridor within 10000 actions.

### 5. [Navigation] LS20: use exp 073 path as verified prefix for next attempt
- **Hypothesis**: Exp 073's path L×3,U×3 reaches the general area. From there, the systematic wall probing begins. This prefix is VERIFIED to work and saves ~6 actions on subsequent attempts.
- **Strategy change**: "Start with verified prefix: L,L,L,U,U,U (from exp 073). This reaches the area near (24,35). Then begin wall probing (idea #1)."
- **Target game**: ls20
- **Expected impact**: Saves 6 actions of exploration.

### 6. [Navigation] LS20: after modifier, switch direction to goal at (34,10)
- **Hypothesis**: After collecting modifier (player sprite ROTATES), goal is at (34,10) — to the RIGHT and UP from modifier (19,30). That's ~3 RIGHT + ~4 UP. The wall at cols 29-33 might need to be crossed AGAIN going RIGHT.
- **Strategy change**: "After modifier collection (player rotates): switch priority to RIGHT > UP. Goal at (34,10) is RIGHT+UP from modifier. You'll need to cross back through the wall gap in the opposite direction."
- **Target game**: ls20
- **Expected impact**: Correct direction after modifier collection.

### 7. [Level Progression] LS20: multi-level data for L2-7
- **Hypothesis**: After L1, known data for subsequent levels.
- **Strategy change**: "L2: start (29,40) → mod RIGHT+DOWN at (49,45) → goal LEFT at (14,40). L4: NO modifier → goal LEFT at (9,5)."
- **Target game**: ls20 L2+
- **Expected impact**: Faster subsequent levels.

### 8. [Level Progression] VC33 L3: stop clicking, conserve lives
- **Hypothesis**: L3 unsolvable. Don't click on L3.
- **Strategy change**: "On L3, stop clicking immediately."
- **Target game**: vc33 L3
- **Expected impact**: Prevents GAME_OVER.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-070**: vc33 L3 — 20 experiments. CLOSED (unsolvable).
- **Stategraph 063 (IMPROVED)**: Center hashing permanent.
- **Executor 064-065**: VC33 L1=3, L2=14.
- **Executor 066-071**: LS20 per-move protocol, batch, smart nav. All 0.
- **Executor 072**: Verified prefix R,U×4,L×3,U×2 leads to DEAD END.
- **Executor 073**: L×3,U×3 reaches (24,35). Modifier at (20,32) — 4 cols apart! **Wall at cols 29-33 blocks.** Need connecting corridor. Player also reached (14,25) by going DOWN-LEFT-UP. GAME_OVER from health.

## Dead Ends (Confirmed)
- **VC33 L3**: UNSOLVABLE. 87 clicks = 0 PPS movement.
- **LS20 verified prefix R,U×4,L×3,U×2**: Dead end (exp 072). Don't use this prefix.
- **LS20 batch moves**: Invisible walls (exp 066)
- ft09, Qwen models, position waypoints, hardcoded paths: all dead ends.

## Key Maze Knowledge (accumulated from exps 069-073)
- Start: (39,45). Modifier: (19,30). Goal: (34,10).
- Wall at cols 29-33 around row 32 separates modifier from approach corridors
- R,U×4,L×3,U×2 = dead end (small room at top)
- L×3,U×3 reaches (24,35) near modifier but wall blocks
- DOWN-LEFT-UP path reaches (14,25) — on modifier's side but too far from it
- Health = 3 hearts, ~18 moves each. Deaths at 206-cell changes.
- The connecting corridor around the wall has NOT been found yet
