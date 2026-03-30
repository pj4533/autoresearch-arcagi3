# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 065): Local scoring = levels solved, NOT RHAE efficiency. L1-2 optimization COMPLETE (L1 in 3 actions, L2 in 14). Only NEW LEVELS change the score. Priority: (1) LS20 L1 — structured maze exploration with persistent mental map, (2) VC33 L3 — btn[0] works ~14% of the time (exp 059); try systematic y-scan and phase-dependent approach, (3) VC33 L3 alternative: find other PPS-moving clicks. ALL ideas are PLAY STRATEGY changes, NOT code changes.**

---

### 1. [Navigation] LS20: persistent map building across deaths (lives 1-2 = explore, life 3 = execute)
- **Hypothesis**: The maze doesn't change between deaths. Each death reveals partial map. Use lives 1-2 for mapping, life 3 to execute the known solution path. Exp 040-041 proved maze IS navigable (DFS reaches 34-46 steps). Exp 064 confirms blind moves don't work.
- **Strategy change**: Add to LS20 strategy: "Build a mental map across deaths. After each move, note: did the move succeed (frame changed) or fail (wall)? After death, you respawn at start but REMEMBER the map. Life 1: explore LEFT+UP toward modifier at (19,30). Life 2: follow known-safe path to frontier, explore further. Life 3: execute the complete path — start (39,45) → modifier (19,30) → goal (34,10). The player sprite ROTATES when collecting the modifier — use this as visual confirmation."
- **Target game**: ls20
- **Expected impact**: Should solve L1 within 3 lives (~54 total moves). L1 baseline=29.

### 2. [Navigation] LS20: wall-following + directional bias (LEFT+UP first)
- **Hypothesis**: Left-hand wall following guarantees systematic coverage. Combined with bias toward LEFT+UP (direction of modifier from start), it efficiently explores toward the goal. Prevents oscillation (exp 033-034's blocker).
- **Strategy change**: Add to LS20 strategy: "Use wall-following: pick a heading (try LEFT first since modifier is LEFT of start). Follow that wall. When you hit a dead end, backtrack and try the next corridor. Bias LEFT+UP — modifier is at (19,30), start is (39,45), so you need to go ~20 cells LEFT and ~15 cells UP. Each move = 5 cells."
- **Target game**: ls20
- **Expected impact**: Prevents oscillation while biasing toward modifier.

### 3. [Hypothesis Testing] VC33 L3: exhaustive y-scan at btn[0] x-position via arc CLI
- **Hypothesis**: Exp 059 showed btn[0] works ~14% of the time — it DOES move PPS but has a low success rate due to sprite overlap. The overlap may be position-dependent: clicking at different y-values at the same x might hit the button instead of the bar. A systematic scan of y=40 to y=60 (display coords) at x=12 would find the exact responsive zone, if one exists. Cost: ~20 lives out of 75.
- **Strategy change**: Add to VC33 L3 strategy: "After solving L1-2, on L3: systematically scan btn[0]'s column. Click at x=12, y=40, then y=42, y=44, ..., y=60. After each click, check `arc state --image` to see if PPS (decoration 14) moved. The y-value where PPS moves = the reliable btn[0] coordinate. This costs ~10-20 clicks but gives definitive data."
- **Target game**: vc33 L3
- **Expected impact**: May find the exact coordinate where btn[0] reliably works. If found, L3 becomes solvable.

### 4. [Hypothesis Testing] VC33 L3: try btn[0] AFTER Phase 1-2 (bar overlap may shift)
- **Hypothesis**: Exp 056 discovered ORDER-DEPENDENT behavior: "btn[7] works after systematic test but NOT when clicked first." Bar positions shift as buttons are clicked, which may change sprite overlaps. If btn[6]×12 is executed first (moving ChX/VAJ), the bar layout shifts enough that btn[0]'s overlap with fCG clears.
- **Strategy change**: Add to VC33 L3 strategy: "CRITICAL: click order matters! The game has state-dependent click behavior. Execute Phase 1 (btn[6]×12 for ChX/VAJ) FIRST. Then try btn[0] — the bar positions may have shifted enough to fix the overlap. Alternate btn[0] with btn[6] or btn[5] (no neutrals needed, saves lives)."
- **Target game**: vc33 L3
- **Expected impact**: If bar shifting fixes the overlap, btn[0] success rate could go from 14% to 100%.

### 5. [Navigation] LS20: frontier-first navigation after respawn
- **Hypothesis**: After respawn, navigate the known-safe path directly to the frontier, then explore new territory. Budget: 70% known-safe path, 30% exploration.
- **Strategy change**: Add to LS20 strategy: "After respawn, DON'T re-explore. Navigate your mental map to the frontier. THEN explore 1-2 new corridors."
- **Target game**: ls20
- **Expected impact**: 2-3x more efficient exploration per life.

### 6. [Navigation] LS20: death-state recording to avoid lethal transitions
- **Hypothesis**: Record which moves at which visual states caused death. Never repeat lethal actions.
- **Strategy change**: Add to LS20 strategy: "When you die, note the last action and what the screen looked like. NEVER repeat that action in that visual state."
- **Target game**: ls20
- **Expected impact**: Eliminates repeat trap deaths.

### 7. [Visual Analysis] LS20: detect modifier and goal sprites visually
- **Hypothesis**: The modifier and goal have distinctive appearances visible within the fog-of-war circle. The player sprite ROTATES when collecting the modifier — use this as confirmation.
- **Strategy change**: Add to LS20 strategy: "Watch for distinctive objects. The modifier and goal look different from walls/floor. When spotted, navigate directly toward them. Your player sprite will visually ROTATE when you step on the modifier — that's how you know you collected it."
- **Target game**: ls20
- **Expected impact**: Goal-directed navigation reduces wasted moves.

### 8. [Puzzle Identification] VC33 L3: alternate btn[0] with real buttons (no neutrals)
- **Hypothesis**: Exp 058 showed neutral clicks cost lives. But alternating btn[0] with btn[6] costs only 2 lives per pair (no neutrals). With 75 lives, that's 37 pairs. At 14% btn[0] success = ~5 PPS moves. Need ~8 total. Not quite enough, but combined with idea #3 (finding the sweet spot y-coordinate), could work.
- **Strategy change**: Add to VC33 L3 strategy: "Alternate btn[0] with btn[6] (never use neutrals — they waste lives). Each btn[6] click moves ChX/VAJ, each btn[0] has ~14% chance of moving PPS. With 37 pairs possible and only 8 PPS moves needed, the math works IF btn[0] success rate is ≥22%."
- **Target game**: vc33 L3
- **Expected impact**: Life-efficient PPS approach. Combined with y-scan (idea #3), may find higher success rate.

### 9. [Puzzle Identification] VC33 L3: try btn[3] at (28,56) — may also control PPS
- **Hypothesis**: The chain is fCG↔sro↔TKb↔nDF↔uUB. PPS sits on sro. Button at game (22,50) / display (28,56) should control TKb→sro transfer = make sro TALLER = push PPS UP. Exp 056 classified btn[3] as "non-button" but maybe it has the SAME sprite overlap problem as btn[0]. A y-scan at x=28 might find it.
- **Strategy change**: Add to VC33 L3 strategy: "Also try scanning x=28 (display) at y=40 to y=60. This is where btn[3] should be — it may control sro (the bar PPS sits on). If btn[3] works, it provides an ALTERNATIVE path to move PPS via the sro↔TKb transfer."
- **Target game**: vc33 L3
- **Expected impact**: Provides a second candidate button for PPS control.

### 10. [Action Efficiency] General: RHAE-aware action budgeting
- **Hypothesis**: RHAE = (human/agent)^2. Baselines: vc33=[6,13,31,59,92,24,82], ls20=[29,41,172,49,53,62,82].
- **Strategy change**: Add to General strategy: "Know the baselines. At 1.5x baseline, STOP exploring and commit. Track your count."
- **Target game**: all
- **Expected impact**: Prevents over-exploration.

### 11. [Level Progression] VC33 L3: life conservation if no PPS solution found
- **Hypothesis**: Levels are sequential — L3 MUST be solved to reach L4. If no PPS workaround is found, conserve lives on L3 (don't click randomly) to extend the session. A NOT_FINISHED on L3 scores 0 for L3+ but doesn't hurt L1-2 scores.
- **Strategy change**: Add to VC33 strategy: "If L3 is unsolvable, stop clicking immediately. Don't waste lives — just let the session end as NOT_FINISHED. This preserves L1-2 scores."
- **Target game**: vc33 L3
- **Expected impact**: Prevents GAME_OVER from wasting lives on L3.

### 12. [Hypothesis Testing] General: periodic context summarization every 10 actions
- **Hypothesis**: Summarizing every ~10 actions prevents loops and maintains strategic focus.
- **Strategy change**: "Every 10 actions: What learned? What changed? Current hypothesis? Next plan?"
- **Target game**: all
- **Expected impact**: Reduces repetitive behavior.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-027**: vc33 L3 bar chart — 6 exps, scoring condition found (markers).
- **Stategraph 028-045**: ls20 navigation — DFS solved (34-46 steps). Center hashing helps.
- **Stategraph 048-062**: vc33 L3 — 14 experiments. PPS button ~14% success rate (exp 059).
- **Stategraph 063 (IMPROVED)**: Center hashing permanent.
- **Executor 064**: VC33 via arc CLI. L1=6, L2=17. L3 PPS broken with vision. ls20=40 blind, 0.
- **Executor 065**: VC33 predict+exact. L1=3 (!), L2=14. Local scoring = levels only, score unchanged.
- **KEY INSIGHTS**: Local score = levels solved / games (not RHAE). btn[0] works ~14% (exp 059). Game click behavior is ORDER-DEPENDENT (exp 056). Player rotates on modifier collection.
