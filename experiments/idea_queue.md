# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 066): Exp 066 showed batch moves FAIL on LS20 — must check frame after EVERY move. The executor needs an explicit per-move wall detection protocol, not just "build a map." Priority: (1) LS20 L1 with per-move frame checking, (2) VC33 L3 btn[0] y-scan + phase-dependent approach. ALL ideas are PLAY STRATEGY changes, NOT code changes.**

---

### 1. [Navigation] LS20: per-move wall detection protocol (REVISED from exp 066 failure)
- **Hypothesis**: Exp 066 used batch moves (multiple `arc action move_X` without checking between them) and many hit walls. The maze has invisible walls — the ONLY way to detect them is checking the frame after EACH move. The protocol must be: move → check → record → repeat.
- **Strategy change**: Replace LS20 strategy with this EXPLICIT protocol:
  ```
  LS20 Per-Move Protocol:
  1. `arc state --image` — look at current frame, note visible corridors
  2. Try move_left (bias LEFT toward modifier at (19,30) from start (39,45))
  3. `arc state --image` — compare to previous frame:
     - If view SCROLLED significantly → move succeeded! Note: "LEFT is open here"
     - If frame looks SAME or barely changed → move BLOCKED by wall. Note: "wall to LEFT here"
  4. If blocked, try move_up (second priority — modifier is also UP from start)
  5. If blocked, try move_right or move_down as fallback
  6. After each successful move, you're at a new position. Repeat from step 1.
  7. Build a mental map: "From start: LEFT works, then LEFT again works, then LEFT blocked so went UP, then LEFT works again..."
  8. After death: replay known-safe path QUICKLY, then explore new territory
  ```
- **Target game**: ls20
- **Expected impact**: Per-move checking eliminates wasted wall-hit actions. Should map modifier path in ~15-25 moves.

### 2. [Navigation] LS20: use `arc state` (text) for fast wall detection between image checks
- **Hypothesis**: Checking `arc state --image` after every move is expensive (each image = context tokens). A faster alternative: use `arc state` (text grid) to detect wall hits. If the text grid changed significantly → move succeeded. If identical or near-identical → blocked. Use `--image` only every 3-5 moves for strategic decisions.
- **Strategy change**: Add to LS20 protocol: "For wall detection, you can use `arc state` (text) instead of `--image` after each move. Just check if the grid output changed from the previous one. Text comparison is faster than image analysis. Use `arc state --image` every 3-5 moves to visually assess the maze layout."
- **Target game**: ls20
- **Expected impact**: Reduces context cost by ~60% while maintaining wall detection accuracy.

### 3. [Navigation] LS20: directional priority order based on known maze layout
- **Hypothesis**: Modifier is at (19,30), start is (39,45). That's ~4 LEFT moves and ~3 UP moves (at 5 cells/move). Goal is at (34,10), which from modifier is ~3 RIGHT and ~4 UP. Directional priority should be: LEFT first (toward modifier), UP second, then RIGHT/DOWN for detours around walls.
- **Strategy change**: Add to LS20 protocol: "Direction priority from start: LEFT > UP > RIGHT > DOWN. You need ~4 LEFT + ~3 UP moves to reach modifier. After modifier (player rotates visually): RIGHT > UP > LEFT > DOWN toward goal. Detour around walls but always return to primary direction."
- **Target game**: ls20
- **Expected impact**: Eliminates random exploration, focuses moves toward known targets.

### 4. [Navigation] LS20: persistent map across deaths — replay fast, then explore
- **Hypothesis**: The maze is static. After death, replay the known-safe path WITHOUT checking frames (you already know these moves work), then switch to per-move protocol at the frontier. This maximizes new territory per life.
- **Strategy change**: Add to LS20 strategy: "After death/respawn: replay your known-safe path as fast commands (no frame checks needed — you KNOW these work). Once at the frontier of explored territory, switch back to per-move protocol. Example: Life 1 discovers 'L,L,U,L,U works'. Life 2 starts with L,L,U,L,U (no checks), then explores from there."
- **Target game**: ls20
- **Expected impact**: Saves 5-10 actions per life by not re-checking known-safe moves.

### 5. [Hypothesis Testing] VC33 L3: exhaustive y-scan at btn[0] x-position via arc CLI
- **Hypothesis**: btn[0] works ~14% at display (12,56). Sprite overlap may be y-dependent. Scanning y=40 to y=60 at x=12 would find the responsive zone. Cost: ~10-20 lives out of 75.
- **Strategy change**: Add to VC33 L3 strategy: "After L1-2, on L3: scan btn[0]'s column. Click at x=12 with y=40,42,44,...,60. Check `arc state --image` after each — did PPS (decoration 14) move? The y-value where PPS moves = reliable coordinate."
- **Target game**: vc33 L3
- **Expected impact**: May find exact coordinate where btn[0] reliably works.

### 6. [Hypothesis Testing] VC33 L3: try btn[0] AFTER Phase 1 (bar overlap may shift)
- **Hypothesis**: Exp 056 showed ORDER-DEPENDENT behavior. After btn[6]×12 (Phase 1), bar positions shift. btn[0]'s overlap with fCG may clear.
- **Strategy change**: Add to VC33 L3 strategy: "Click order matters! Execute btn[6]×12 FIRST (alternating with btn[5] to avoid neutrals). THEN try btn[0]. Bar positions may have shifted enough to fix overlap."
- **Target game**: vc33 L3
- **Expected impact**: btn[0] success rate could increase from 14% to higher after Phase 1.

### 7. [Puzzle Identification] VC33 L3: try btn[3] at display (28,56) as alternative PPS control
- **Hypothesis**: btn[3] at display (28,56) should control TKb→sro transfer. If sro grows, PPS moves UP. Exp 056 classified it as "non-button" but it may have the same overlap issue. Y-scan at x=28 might find it.
- **Strategy change**: Add to VC33 L3 strategy: "Also scan x=28 at y=40-60. btn[3] may control sro (PPS's bar). If it works, it's an alternative PPS-UP path."
- **Target game**: vc33 L3
- **Expected impact**: Second candidate button for PPS control.

### 8. [Puzzle Identification] VC33 L3: alternate btn[0] with btn[6] (no neutrals)
- **Hypothesis**: Alternating two real buttons avoids neutral-click life waste. btn[6]+btn[0] pairs cost 2 lives each. With 75 lives = 37 pairs. At ≥22% btn[0] success = enough for 8 PPS moves.
- **Strategy change**: "Alternate btn[0] with btn[6]. No neutrals. Each pair = 2 lives. Need btn[0] ≥22% success rate for the math to work."
- **Target game**: vc33 L3
- **Expected impact**: Life-efficient if btn[0] success rate can reach 22%+.

### 9. [Visual Analysis] LS20: detect modifier/goal sprites and player rotation
- **Hypothesis**: Modifier and goal have distinctive visual appearances. Player sprite ROTATES when stepping on modifier — visual confirmation of collection.
- **Strategy change**: "Watch for distinctive colored objects. Your player visually ROTATES on modifier collection."
- **Target game**: ls20
- **Expected impact**: Goal-directed navigation when targets are visible.

### 10. [Action Efficiency] General: RHAE-aware action budgeting
- **Hypothesis**: RHAE = (human/agent)^2. Baselines: vc33=[6,13,31,...], ls20=[29,41,172,...].
- **Strategy change**: "Track action count. At 1.5x baseline, commit to your plan."
- **Target game**: all
- **Expected impact**: Prevents over-exploration.

### 11. [Level Progression] VC33 L3: life conservation if unsolvable
- **Hypothesis**: If L3 can't be solved, stop clicking. NOT_FINISHED preserves L1-2 scores.
- **Strategy change**: "If L3 is unsolvable, stop clicking immediately."
- **Target game**: vc33 L3
- **Expected impact**: Prevents GAME_OVER from random L3 clicks.

### 12. [Hypothesis Testing] General: periodic summarization every 10 actions
- **Hypothesis**: Summarizing every ~10 actions prevents loops.
- **Strategy change**: "Every 10 actions: What learned? What changed? Next plan?"
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
- **Executor 065**: VC33 predict+exact. L1=3 (!), L2=14. Local scoring = levels only.
- **Executor 066**: LS20 vision-guided map building. 90 actions, 0. **Batch moves fail — many hit walls. Need per-move frame checking.**
- **Executor 067**: VC33 L3 btn[0] y-scan. SCALED coords (24,112) = display*2 work! PPS moved 2 rows in 30 clicks. Need 60+ btn[0] clicks for full PPS movement — budget insufficient after L1+L2+P1-2.
- **KEY INSIGHTS**: Batch moves DON'T WORK on LS20 (invisible walls). Must check frame after EACH move. **btn[0] WORKS at SCALED coords (24,112)** ~14% success rate. Need 60+ btn[0] clicks for full Phase 3. Game click behavior is ORDER-DEPENDENT (exp 056). Player rotates on modifier collection.
