# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 070): VC33 L3 is CLOSED — unsolvable (exp 068 + 070: 87 clicks at every position, 0 PPS movement). ALL score improvement comes from LS20. Exp 069 validated per-move protocol but agent OVERSHOT the modifier (L×5+U×3 vs needed L×4+U×3). Key fix: switch to LOCAL SEARCH after ~7 directional moves. ALL ideas are PLAY STRATEGY changes, NOT code changes.**

---

### 1. [Navigation] LS20: local search after ~7 directional moves (ADDRESSES exp 069 overshoot)
- **Hypothesis**: Exp 069 moved L×5+U×6 but modifier is at ~L×4+U×3 from start. The agent PASSED the modifier area. After ~7 successful moves in the correct direction (LEFT/UP), the agent should STOP biasing and switch to local search: try ALL 4 directions systematically at each position. The modifier is nearby but may require a RIGHT or DOWN detour to reach.
- **Strategy change**: Add to LS20 strategy: "After 7 successful LEFT/UP moves, you're in the modifier zone. STOP biasing LEFT/UP. Instead, try ALL 4 directions at each position — the modifier may be behind you or to the side. Spend 5-10 moves searching locally. Look for the modifier sprite (distinctive colored object) or player rotation (= collected modifier)."
- **Target game**: ls20
- **Expected impact**: Prevents overshooting. Local search in a 5×5 cell area should find the modifier within 10 moves.

### 2. [Navigation] LS20: increase action budget to 500+ (exp 069 had only 45)
- **Hypothesis**: Exp 069 used only 45 actions on ls20 — not enough for maze exploration. The play_strategy already says "500+" but the executor ran with a smaller budget. With 500 actions: ~250 real moves (at 50% wall-hit rate), enough for multiple deaths + replays + full exploration.
- **Strategy change**: Update play_strategy: "Use `arc start ls20 --max-actions 500`. VC33 only needs ~20 actions total. Dedicate the remaining budget to ls20. 500 actions gives room for 3+ death/replay cycles and thorough exploration."
- **Target game**: ls20
- **Expected impact**: Removes the budget constraint that limited exp 069.

### 3. [Navigation] LS20: death-replay strategy (explore → die → replay → explore further)
- **Hypothesis**: With 3 hearts (~18 moves each = ~54 moves per life), each death explores ~20 real moves of new territory. After death, replay the known-safe path (fast, no checks) then explore at the frontier. 3 lives × 20 new moves = 60 real moves = enough to cover the ~14-move solution path plus detours.
- **Strategy change**: Add to LS20 strategy: "Each death teaches you the maze. Life 1: explore LEFT+UP, record every successful move. Life 2: replay Life 1's successful moves FAST (no frame checks — you know they work), then explore new territory at the frontier. Life 3: replay combined path, hopefully reach modifier then goal."
- **Target game**: ls20
- **Expected impact**: 3 lives × 20 new moves = 60 total explored moves. Solution path is ~14-15 direct moves + maze detours.

### 4. [Navigation] LS20: smarter wall probing — avoid re-trying blocked directions
- **Hypothesis**: Exp 069 had 55% wall-hit rate. Some of those were re-trying directions known to be blocked. The agent should track which directions are blocked at each "position" (identified by frame hash or cell count pattern).
- **Strategy change**: Add to LS20 strategy: "At each position, track which directions you've tried: 'Position A: LEFT=open, UP=blocked, RIGHT=untried, DOWN=untried.' Never re-try a blocked direction at the same position. After death, your direction knowledge persists — replay the successful path AND remember which directions were blocked."
- **Target game**: ls20
- **Expected impact**: Reduces wall-hit rate from 55% to ~25%, nearly doubling effective moves per action.

### 5. [Visual Analysis] LS20: what the modifier and goal look like
- **Hypothesis**: Exp 069 reached the modifier area but couldn't identify it visually. The agent needs to know what to look for. The modifier should be a small colored sprite distinct from walls (yellow) and floor (green). The player ROTATES when it collects the modifier.
- **Strategy change**: Add to LS20 strategy: "The modifier is a small colored object that looks DIFFERENT from walls and floor. It may be partially hidden behind walls. Look carefully at the frame image for any small colored blob that isn't a wall or path tile. When you step on it, your player sprite ROTATES — this is the ONLY reliable confirmation of collection. After rotation, switch direction to RIGHT+UP toward goal."
- **Target game**: ls20
- **Expected impact**: Helps executor identify the modifier visually when in range.

### 6. [Navigation] LS20: multi-level data (L2-7 directions after solving L1)
- **Hypothesis**: After solving L1, immediate next-level data saves exploration time.
- **Strategy change**: "After L1: L2 start (29,40) → mod RIGHT+DOWN at (49,45) → goal LEFT at (14,40). L3 start (9,45) → mod RIGHT+UP at (49,10) → goal RIGHT+DOWN at (54,50). L4 start (54,5) → NO modifier → goal LEFT at (9,5). L5-7 similar patterns."
- **Target game**: ls20 L2+
- **Expected impact**: Faster subsequent levels.

### 7. [Action Efficiency] General: RHAE-aware budgeting
- **Hypothesis**: LS20 L1 baseline=29. At 50 actions: (29/50)^2 = 34%. At 100 actions: 8%. At 40: 53%. Aim for <60 total actions.
- **Strategy change**: "LS20 L1 baseline is 29 actions. Target: <60 total. Even 100 actions gives 8% — any positive score beats 0%."
- **Target game**: ls20
- **Expected impact**: Sets action count target.

### 8. [Level Progression] VC33 L3: conserve lives, end as NOT_FINISHED
- **Hypothesis**: L3 is confirmed unsolvable. Don't click ANYTHING on L3 — preserve lives, end session.
- **Strategy change**: "On L3, stop clicking. Let the session end as NOT_FINISHED. DO NOT attempt L3."
- **Target game**: vc33 L3
- **Expected impact**: Prevents GAME_OVER from L3 life waste.

### 9. [Hypothesis Testing] General: periodic summarization every 10 actions
- **Hypothesis**: Prevents loops and maintains focus.
- **Strategy change**: "Every 10 actions: What learned? What changed? Next plan?"
- **Target game**: all
- **Expected impact**: Reduces repetitive behavior.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-027**: vc33 L3 bar chart — 6 exps, scoring condition found (markers).
- **Stategraph 028-045**: ls20 navigation — DFS solved (34-46 steps). Center hashing helps.
- **Stategraph 048-062**: vc33 L3 — 14 experiments.
- **Stategraph 063 (IMPROVED)**: Center hashing permanent.
- **Executor 064-065**: VC33 L1=3, L2=14. L3 PPS broken. ls20 blind=0.
- **Executor 066**: LS20 batch moves fail. Need per-move frame checking.
- **Executor 067-068**: btn[0] y-scan + 57-click definitive test. btn[0] DEAD at ALL coords.
- **Executor 069**: LS20 per-move protocol WORKS (2 cells=blocked, 52+=move). But only 45 actions → 20 real moves → overshot modifier. Need more budget + local search.
- **Executor 070**: VC33 L3 grid scan: 30 positions, 0 PPS movement. **L3 CLOSED — unsolvable.**

## Dead Ends (Confirmed)
- **VC33 L3 entirely**: btn[0] broken (57 clicks=0, exp 068), full grid scan=0 (30 positions, exp 070). NO mechanism to move PPS. UNSOLVABLE in this game instance.
- Batch moves on LS20 (invisible walls, exp 066)
- All local Qwen models for reasoning
- ft09 game version broken
- Position-based waypoints (tracking unreliable)
- Hardcoded paths from source (collision model proprietary)
