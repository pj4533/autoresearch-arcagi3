# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 068): btn[0] is DEAD — 57 clicks, 0 PPS movement, definitively broken. ALL btn[0] ideas purged. LS20 L1 is now the ONLY path to score improvement. If LS20 L1 solved: local score goes from 0.6667 → 1.0 (+50%). VC33 L3 has ONE remaining angle: btn[3] at display (28,56). ALL ideas are PLAY STRATEGY changes, NOT code changes.**

---

### 1. [Navigation] LS20: per-move wall detection protocol (CRITICAL — exp 066 lesson)
- **Hypothesis**: Exp 066 proved batch moves fail. Must check frame after EACH move. The protocol:
- **Strategy change**: Replace LS20 strategy with:
  ```
  LS20 Per-Move Protocol:
  1. `arc state --image` — look at current frame, note visible corridors
  2. Try move_left (bias LEFT toward modifier from start)
  3. `arc state --image` — compare to previous:
     - View SCROLLED → move succeeded! Note: "LEFT open here"
     - Frame SAME → wall hit! Note: "wall LEFT here". Try move_up.
  4. If blocked LEFT+UP, try RIGHT or DOWN as detour
  5. After each successful move, repeat from step 1
  6. Build mental map: "From start: L works, L works, L blocked→went U, L works..."
  7. After death: replay known-safe path fast, then explore at frontier
  ```
- **Target game**: ls20
- **Expected impact**: Eliminates wasted wall-hit actions. Should map modifier path in ~20 moves.

### 2. [Navigation] LS20: directional priority based on known positions
- **Hypothesis**: Start (39,45) → Modifier (19,30): ~4 LEFT + ~3 UP. Modifier → Goal (34,10): ~3 RIGHT + ~4 UP. Direction priority should match these vectors.
- **Strategy change**: Add to LS20: "From start: try LEFT first, UP second, RIGHT/DOWN only for detours. After modifier collection (player visually ROTATES): try RIGHT first, UP second. You need ~4L+3U to modifier, then ~3R+4U to goal. Each move = 5 cells."
- **Target game**: ls20
- **Expected impact**: Focuses exploration in the correct direction.

### 3. [Navigation] LS20: use `arc state` text for fast wall detection
- **Hypothesis**: Full `arc state --image` after every move is expensive. Use `arc state` (text) to detect wall hits — just check if output changed. Use `--image` every 3-5 moves for strategic decisions.
- **Strategy change**: "For wall detection: `arc state` (text) after each move. If text changed → moved. If same → wall. Use `arc state --image` every 3-5 moves to see the maze visually."
- **Target game**: ls20
- **Expected impact**: Reduces context cost ~60% while maintaining wall detection.

### 4. [Navigation] LS20: replay known-safe path after death, then explore
- **Hypothesis**: Maze is static. After death, replay known-safe moves WITHOUT checking (already verified). Switch to per-move protocol at frontier.
- **Strategy change**: "After death: replay your verified path fast (no frame checks needed). At frontier, switch to per-move protocol. Example: Life 1 maps 'L,L,U,L,U'. Life 2 starts: L,L,U,L,U (no checks), then explores new territory."
- **Target game**: ls20
- **Expected impact**: Saves 5-10 actions per life on re-exploration.

### 5. [Visual Analysis] LS20: detect modifier/goal visually + player rotation confirmation
- **Hypothesis**: Modifier and goal have distinctive appearances. Player sprite ROTATES when stepping on modifier. This is the only reliable collection confirmation.
- **Strategy change**: "Watch for distinctive colored objects in the visible circle. Your player visually ROTATES on modifier collection — that's how you know you got it. After rotation, switch direction priority toward goal (RIGHT+UP)."
- **Target game**: ls20
- **Expected impact**: Confirms modifier collection without position tracking.

### 6. [Hypothesis Testing] VC33 L3: try btn[3] at display x=28 (LAST remaining PPS option)
- **Hypothesis**: btn[0] is dead. But btn[3] at display (28,56) was NEVER y-scanned. It should control TKb→sro transfer (making sro taller = PPS moves UP). Exp 056 classified it as "non-button" but never tried y-offsets. If btn[3]'s overlap is different from btn[0]'s, it might work.
- **Strategy change**: "On L3: scan x=28 at y=40,42,44,...,60. Check if PPS (decoration 14) moves after each click. Also try x=24,26,30 at y=56. This is the LAST untested PPS approach — if it fails, L3 is unsolvable."
- **Target game**: vc33 L3
- **Expected impact**: If btn[3] works, L3 becomes solvable. If not, L3 is confirmed unsolvable.

### 7. [Puzzle Identification] VC33 L3: explore ALL clickable positions for hidden PPS mechanic
- **Hypothesis**: Maybe PPS can be moved by clicking something OTHER than a button — the decoration itself, the bar it sits on, the gap between bars, or a hidden element. The game has 75 lives; a systematic 5×5 grid of clicks across the screen (25 lives) could reveal any hidden interactive element.
- **Strategy change**: "If btn[3] fails: try clicking at a grid of positions across the screen — (10,10), (20,10), (30,10), ..., (50,50). Check if PPS moves after each. This discovers ANY hidden mechanic that moves PPS."
- **Target game**: vc33 L3
- **Expected impact**: Discovers hidden mechanics if they exist. Definitive test.

### 8. [Level Progression] VC33 L3: conserve lives if unsolvable
- **Hypothesis**: If all PPS approaches fail, stop clicking on L3. NOT_FINISHED preserves L1-2 scores. Don't GAME_OVER from random clicks.
- **Strategy change**: "If L3 is confirmed unsolvable, stop clicking immediately. Let the session end as NOT_FINISHED."
- **Target game**: vc33 L3
- **Expected impact**: Prevents GAME_OVER life waste.

### 9. [Action Efficiency] General: RHAE-aware budgeting
- **Hypothesis**: RHAE = (human/agent)^2. LS20 L1 baseline=29. At 50 actions: 34% score. At 40: 53%.
- **Strategy change**: "Track action count vs baselines. For LS20 L1: aim for <45 actions total."
- **Target game**: all
- **Expected impact**: Prevents over-exploration.

### 10. [Navigation] LS20: multi-level data for after L1
- **Hypothesis**: If L1 is solved, L2-7 have known start/modifier/goal positions. Pre-loading this data saves exploration time on subsequent levels.
- **Strategy change**: "After L1, known level data: L2: start (29,40) → mod (49,45) → goal (14,40). L3: start (9,45) → mod (49,10) → goal (54,50). L4: start (54,5) → goal (9,5) NO MODIFIER. Apply same per-move protocol with adjusted direction priorities."
- **Target game**: ls20 L2+
- **Expected impact**: Faster subsequent level solving with pre-known positions.

### 11. [Hypothesis Testing] General: periodic summarization every 10 actions
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
- **Executor 067-068**: btn[0] y-scan + 57-click definitive test. **btn[0] DEAD at ALL coords.** 0 PPS movement.
- **Explorer 001-030**: All score 0.

## Dead Ends (Confirmed)
- **btn[0] at ANY coordinate**: Display coords, scaled coords, y=40-60, x=6-14, (24,112). 57 consecutive clicks = 0. DEAD.
- Batch moves on LS20 (invisible walls)
- All local Qwen models for reasoning
- ft09 game version broken
- Position-based waypoints (tracking unreliable)
- Hardcoded paths from source (collision model proprietary)
- Brute-force/uniform clicking vc33
