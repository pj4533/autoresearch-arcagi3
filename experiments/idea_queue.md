# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 061): PIVOT from VC33 L3 (13 experiments, PPS button blocked by sprite overlap). Focus on: (1) VC33 L1-2 optimization — quadratic scoring means fewer clicks = much better scores, (2) LS20 with center hashing + natural DFS, (3) VC33 L3 via arc CLI as a stretch goal.**

---

### 1. [Action Efficiency] VC33 optimize L1-2 click counts for better per-level scores
- **Hypothesis**: Scoring formula is QUADRATIC: (human/agent)^2. If level 1 baseline is 6 clicks and agent uses 12, score = (6/12)^2 = 0.25. If agent uses 7, score = (6/7)^2 = 0.73. Current trial-and-lock uses several trial clicks + execution clicks — can be optimized.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Level 1 (2 buttons): 2 trial clicks + measure imbalance change. Lock best. Click exactly `gap / change_per_click` times. Minimize total.
  2. Level 2 (4 buttons, needs cycling): 4 trial clicks + faster plateau detection + optimal cycling.
  3. Track per-level click counts and compare to baselines (L1=6, L2=13).
- **Target game**: vc33
- **Expected impact**: Better per-level scores on already-solved levels. Even small improvements compound due to quadratic formula.

### 2. [Navigation] LS20 natural DFS with center hashing + correct start position
- **Hypothesis**: Exp 050 showed center hashing (20×20 region) changed ls20 from GAME_OVER to NOT_FINISHED. Combined with the confirmed start position (39,45) and natural DFS exploration (no position-based bias), the agent should explore the maze more effectively. Iterative deepening across deaths (exp 039-041) already reaches 34-46 steps.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Apply center 20×20 hashing (from exp 050)
  2. Use correct start position (39,45) for any position logic
  3. Remove ALL waypoint/position-based directional bias
  4. Ensure state graph persists across deaths
  5. Increase max_actions to 2000+
- **Target game**: ls20
- **Expected impact**: With reliable hashing and enough exploration budget, DFS should find modifier→goal path.

### 3. [Stretch] VC33 L3 via arc CLI manual play
- **Hypothesis**: The stategraph agent can't reliably press the PPS-UP button (btn[0]) due to sprite overlap. But the executor (Claude Code with vision) can play via arc CLI, visually verify each click, and adjust coordinates in real-time.
- **Changes**: Play L3 manually after auto-solving L1-2:
  ```bash
  arc start vc33 --max-actions 75
  # L1-2 auto-solve, then on L3:
  arc state --image
  # Visually identify buttons and decorations
  # Click btn[6] area, verify ChX/VAJ moved
  # Click near (12,56) area with slight offsets until PPS moves
  # Execute plan visually
  ```
- **Known plan (if PPS-UP works):**
  - Phase 1: btn[6]=(46,56) × 12 — ChX DOWN, VAJ UP
  - Phase 2: btn[4]=(34,56) × 4 — VAJ correct
  - Phase 3: PPS-UP × 8 — PPS to target
- **Target game**: vc33 level 3
- **Expected impact**: Solves L3 if PPS button can be found visually.

### 4. [Navigation] LS20 level data for all 7 levels (pre-computed)
- **Per-level data (from source):**
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

### 5. [Level Progression] VC33 level 4+ investigation
- **Hypothesis**: Levels 4-7 may have different mechanics. Low priority until L3 solved or bypassed.
- **Target game**: vc33

---

## Completed

- **Stategraph 019 (BREAKTHROUGH)**: Balance puzzle → score 0.3333.
- **Stategraph 021 (IMPROVED)**: Trial-and-lock → score 0.6667.
- **Stategraph 022-027**: vc33 L3 bar chart — 6 exps, scoring condition found (markers).
- **Stategraph 028-045**: ls20 navigation — DFS solved (34-46 steps). Start position confirmed (39,45). State matching is blocker. Center hashing helps.
- **Stategraph 046-047**: ls20 confirmed (39,45), vc33 L3 decoded as chain-of-bars.
- **Stategraph 048-061**: vc33 L3 — 13 experiments. Phase 1-2 work (ChX/VAJ reach targets). Phase 3 (PPS) BLOCKED: btn[0] at game(6,50) overlaps with fCG rDn bar, get_sprite_at returns wrong sprite ~86% of time. 38 experiments at plateau.
- **Explorer 001-030**: All score 0.
- **KEY INSIGHTS**: Coordinate mapping is display=game+6 (not scaling). Scoring is quadratic (human/agent)^2. VC33 grid sizes: L1-2=32, L3=52, L4-6=64, L7=48.
