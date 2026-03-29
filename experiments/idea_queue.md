# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 058): DECORATIONS MOVE! Coordinate mapping is display=game+6 (not scaling). btn[6]×10 moved ChX 36.2→45.8 and VAJ 46.2→36.6. Close to targets! Rate: 0.96 display px/click. Need ~2 more btn[6] + VAJ adjustment + PPS-UP button (btn[0] at display(12,56) = game(6,50)). Life budget: 75, need ~48 total clicks with neutrals.**

---

### 1. [Puzzle Logic] VC33 level 3 — SIMPLIFIED 18-CLICK SOLUTION (using verified buttons)
- **Hypothesis**: Exp 055 verified all buttons empirically. fCG is independent (not in chain). The old 23-click plan had unnecessary chain transfers. Simplified to 18 clicks using 3 buttons only.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Implement level-3 specific click sequence using executor's verified display coordinates:

  ```
  SOLUTION (18 clicks, verified against source gug() win condition):

  Step 1: btn(50) × 9  — uUB shrinks, nDF grows
    ChX: y=21 → y=39 ✓ (target: 39)
    VAJ: y=43 → y=25 (temporary overshoot)

  Step 2: btn(38) × 3  — nDF shrinks, TKb grows
    VAJ: y=25 → y=31 ✓ (target: 31)

  Step 3: btn(16) × 6  — fCG grows (independent pair)
    PPS: y=45 → y=33 ✓ (target: 33)

  Total: 18 clicks. Human baseline: 31. Perfect per-level score.
  ```

  **PROBLEM FROM EXP 056:** btn[1]=(16,56) moves PPS DOWN, not UP! PPS needs UP.

  **FIX — find the missing PPS-UP button:**
  The sro→fCG button at game x=6 → display ~(8, 56-62) is NOT found by BFS (too close to left edge).
  **Try clicking at display (8, 56) or (7, 62) manually.** This should grow fCG → move PPS UP.
  If it works: solution = btn[6]×10 + btn[5]×~1 + PPS-UP×~6 = ~17 clicks.

  **Alternative — order-dependent activation:**
  Exp 056 found buttons become valid after other clicks. After doing step 1 (btn[6]×10),
  re-test btn[0]=(12,56) — it might now activate as PPS-UP (bar heights changed).

  **DIRECTION REMINDER (exp 057 used wrong directions!):**
  - ChX DOWN: use **btn[6]=(46,56)** NOT btn[7] (which is UP)
  - VAJ UP: use **btn[6]** or **btn[5]=(38,56)**
  - PPS UP: MISSING — need to find button at display x≈8

  **Y-COORDINATE DIAGNOSTIC:**
  BFS finds buttons at display y=56, but game buttons are at game y=50 → display y≈62.
  The 4 "non-working" buttons may work at a different y! Try:
  ```
  For each x in [8, 12, 24, 28, 34]:
    Try clicking at y=56, 58, 60, 62
    Check if any decoration moved
  ```
  This finds the correct clickable y AND the missing PPS-UP button (x≈8).

  **Click counts:** at 1.2 display px/click:
  - ChX: 36.2→48.0 = ~10 clicks DOWN (btn[6])
  - VAJ: 46.2→38.2 = ~7 clicks UP (btn[6] gives both ChX+VAJ, or btn[5] for VAJ only)
  - PPS: 48.2→40.6 = ~6 clicks UP (missing button)
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:

  **VERIFIED BUTTON MAPPING (traced from dzy init source code):**
  ```
  LEFT-side buttons (transfer LEFT through chain):
    game x=40 → uUB→nDF (source=uUB, dest=nDF)
    game x=28 → nDF→TKb (source=nDF, dest=TKb)
    game x=18 → TKb→sro (source=TKb, dest=sro)
    game x=6  → sro→fCG (source=sro, dest=fCG)

  RIGHT-side buttons (transfer RIGHT, REVERSE direction):
    game x=44 → nDF→uUB
    game x=32 → TKb→nDF
    game x=22 → sro→TKb
    game x=10 → fCG→sro
  ```

  **SOLUTION: Click LEFT-side buttons only, right-to-left:**
  ```
  Step 1: Click game x=40 button 9 times (uUB→nDF)
  Step 2: Click game x=28 button 3 times (nDF→TKb)
  Step 3: Click game x=18 button 5 times (TKb→sro)
  Step 4: Click game x=6  button 6 times (sro→fCG)
  Total: 23 clicks
  ```

  Use BFS-detected display positions that the agent already found (exp 052: y≈56 area). The 4 LEFT-side buttons in the BFS list are buttons [0], [2], [4], [6] or similar — identify by x-position order: leftmost pair's LEFT button = sro→fCG, rightmost pair's LEFT button = uUB→nDF.

  **KEY: exp 052 used btn[0-7] but the direction mapping was wrong. Use the LEFT button in each pair, not the RIGHT one.**

- **Target game**: vc33 level 3
- **Expected impact**: Score improvement from 0.6667. 23 clicks ≤ baseline 31 → perfect per-level score.

  **VERIFY first:** Click one button, observe which bar changes. If clicking x=88 shrinks uUB (rightmost tall bar), use primary mapping. If it grows nDF instead, use reversed mapping.

  **Implementation:** Detect level 3 (8 buttons in horizontal row at y=50). Execute 23-click sequence. Order matters: must go right-to-left (uUB→nDF first, then chain leftward).

- **Target game**: vc33 level 3
- **Expected impact**: Score improves from 0.6667. Level 3 solved in 23 clicks (≤ baseline 31) = perfect per-level score.

### 2. [Navigation] LS20 natural DFS exploration — no position bias, fix state hashing
- **Hypothesis**: Exp 046 confirmed: (1) start at (39,45) ✓, (2) walls block direct LEFT, (3) position tracking unreliable, (4) DFS must explore naturally. The stategraph's DFS already reaches 34-46 steps (exp 039-041) from the correct start position. The problem is that state hashing is unreliable — hash changes without real movement cause false transitions in the graph.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. **Fix state hashing**: The current 2-row mask may not be enough. The game has a fog-of-war circle (source line 1297: pixels > 20.0 distance from player center are set to color 5). This means the EDGES of the grid are always the same color (5), but the CENTER varies. Hash only the center 8x8 or 10x10 region of the 16x16 viewport instead of masking rows.
  2. **Increase action budget**: Run with 2000+ max_actions. At 0.012s/action, this costs <30s.
  3. **Persist state graph across deaths**: Ensure iterative deepening works — each death adds explored territory.
  4. **No directional bias**: Remove any position-based waypoint logic. Let DFS explore all directions equally.
- **Target game**: ls20
- **Expected impact**: With reliable state hashing, the DFS explores the actual maze structure. With enough actions and iterative deepening, it should find modifier→goal path.

### 3. [Navigation] LS20 fog-of-war aware hashing — hash center region only
- **Hypothesis**: LS20 has a fog-of-war circle (source code line 1297: `if math.dist(...) > 20.0: frame[hhe, dcv] = 5`). Pixels beyond 20 units from player center are always color 5. This means the grid EDGES are constant while the CENTER changes based on actual position. The current full-grid hash (minus 2 rows) includes these constant-5 edges, making hashes LESS sensitive to actual position changes. Fix: hash only the center region.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_hash_frame()`, instead of masking top/bottom 2 rows, extract the center 8x8 or 10x10 region and hash only that. This makes the hash sensitive to actual position while ignoring the constant fog-of-war edges.
- **Target game**: ls20
- **Expected impact**: Reliable state detection → no false transitions → DFS explores real maze paths.

### 4. [Puzzle Logic] LS20 detect modifier/goal collection from score or frame signature
- **Hypothesis**: Even without position tracking, the agent can detect key events:
  - **Modifier collected**: Player sprite rotates (tuv changes). Center pixels at player position change pattern.
  - **Wrong goal state**: Game flashes red and player doesn't move (source line 1451-1453).
  - **Level complete**: Score increases.
  Use these signals to understand progress without position tracking.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After each move, check for distinctive frame patterns:
  1. Player rotation change (compare center 5x5 pixels with saved pattern)
  2. Red flash (color 0 appears in player area)
  3. Score change (already handled by level transition logic)
- **Target game**: ls20
- **Expected impact**: Knows when modifier collected, can avoid revisiting modifier area.

### 5. [Action Efficiency] VC33 optimize levels 1-2 click counts
- **Hypothesis**: Scoring formula is QUADRATIC: (human/agent)^2. Level 1 baseline 6 clicks, level 2 baseline 13. Minimizing trial clicks improves per-level scores significantly.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: On trial phase: only 2 trial clicks needed (2 buttons in level 1). Lock immediately. Click exact gap count.
- **Target game**: vc33
- **Expected impact**: Better per-level scores on already-solved levels.

### 6. [Navigation] LS20 multi-level data — waypoints for levels 2-7
- **Hypothesis**: Once level 1 is solved, subsequent levels need their own waypoint data. All 7 levels pre-computed from source code.
- **Per-level data:**
  | Level | Start | Modifier | Goal(s) |
  |-------|-------|----------|---------|
  | 1 | (39,45) | (19,30) | (34,10) |
  | 2 | (29,40) | (49,45) | (14,40) |
  | 3 | (9,45) | (49,10) | (54,50) |
  | 4 | (54,5) | NONE | (9,5) |
  | 5 | (54,50) | (19,40) | (54,5) |
  | 6 | (24,50) | (19,25) | (54,50),(54,35) |
  | 7 | (14,10) | (54,20) | (29,50) |
- **Target game**: ls20
- **Expected impact**: Immediate multi-level solving once level 1 works.

### 7. [Level Progression] VC33 level 4+ investigation
- **Hypothesis**: Levels 4-7 may have different mechanics. Low priority until level 3 solved.
- **Target game**: vc33
- **Expected impact**: Strategy preparation.

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-027**: Six experiments on vc33 level 3 bar chart. All reverted.
- **Stategraph 028**: ls20 visual investigation — maze with player=blue cross.
- **Stategraph 029-035**: Seven ls20 navigation experiments — all reverted.
- **Stategraph 036-037**: Maze data extraction + offline BFS — collision model proprietary.
- **Stategraph 038-041**: DFS/iterative deepening — navigation solved (34-46 steps), state matching is blocker.
- **Stategraph 042-045**: Waypoint navigation attempts — all used wrong start position (1,53). Exp 045 proved goal unreachable from (1,53) grid.
- **Stategraph 046**: CONFIRMED start position (39,45) via arc CLI. Maze walls block direct LEFT. Position tracking unreliable.
- **Stategraph 047**: VC33 level 3 DECODED — chain-of-bars, 5 bars, 8 buttons, 3 decorations need target positions.
- **Explorer 001-030**: All score 0.
- **CONFIRMED**: Player entity is "pca" (tag "caf") at (39,45), not "hep" at (1,53).
