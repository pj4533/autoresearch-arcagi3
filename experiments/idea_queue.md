# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**ALL 25 GAMES ATTEMPTED. Score: 3/25 unique (12%). Phase: RETRY.**

> **STOP replaying su15/sb26/re86** — they've been scored 7 times total across 3 games. You know how to play them. The ONLY way to improve is converting NEW games from 0→1.
>
> **12 games had ≤7 actions — RETRY THESE WITH 15+ ACTIONS EACH:**
> 1. **lp85** (0 actions!) — apply grid parsing, try ALL action types
> 2. **sk48** (0 actions!) — apply grid parsing, try ALL action types
> 3. **m0r0** (1 action) — apply full protocol
> 4. **tr87** (3 actions) — symbol tiles with reference below = zone detection pattern
> 5. **s5i5** (3 actions) — apply full protocol
> 6. **ft09** (5 actions) — 4-quadrant pattern = grid parsing + counter monitoring
> 7. **sc25** (5 actions) — apply full protocol
> 8. **g50t** (5 actions) — apply full protocol
> 9. **lf52** (5 actions) — apply full protocol
> 10. **cd82** (6 actions) — apply full protocol
> 11. **dc22** (7 actions) — apply full protocol
> 12. **vc33** (7 actions) — counter game, apply counter monitoring
>
> **ON EVERY RETRY**: Take at least 15 actions. Use grid analysis. Test all action types. Try perform early. Look for zones (reference/workspace/toolbox). Check counters.
>
> **WHAT WORKS**: Grid parsing, zone detection, constraint satisfaction, select→apply sequences.

---

### 1. [Visual Analysis] Mathematical Grid Parsing — Use Numbers, Not Just Eyes
- **Hypothesis**: The su15 breakthrough came from analyzing the grid DATA numerically — finding precise pixel coordinates, computing distances between objects, identifying mathematical patterns (e.g., dots at +2 cols, -2 rows each). This is something an LLM can do that pure vision can't. Generalizing this approach to all games could unlock more scoring.
- **Strategy change**: Add to play_strategy.md: "GRID ANALYSIS RULE: Don't just LOOK at the frame — ANALYZE it numerically. After `arc state --image`, also examine the raw grid data. (a) List all non-background pixels by color and exact (row, col) position. (b) Look for mathematical relationships: equally-spaced objects, diagonal lines, symmetry axes, paired objects at mirror positions. (c) Compute distances between similar-colored objects. (d) Identify paths, lines, or connections between objects. This numerical analysis revealed the solution in su15 and is likely the key to many click-based games."
- **Expected impact**: Directly generalizes what worked in the first scored game. Mathematical patterns are invisible to casual visual inspection but obvious to numerical analysis. High probability of unlocking click-based games (vc33, ft09, tr87).

### 2. [Pattern Recognition] Reference-Workspace-Toolbox Zone Detection
- **Hypothesis**: sb26 breakthrough revealed a common game layout: one zone shows the TARGET (what to achieve), another is the WORKSPACE (where you act), and a third provides TOOLS (colors, pieces, options). Recognizing this layout instantly reveals the goal and available mechanics.
- **Strategy change**: Add to play_strategy.md: "ZONE DETECTION: Many games divide the screen into functional zones. Look for: (a) REFERENCE/TARGET zone — shows what the finished result should look like (often top or side). (b) WORKSPACE zone — the area you manipulate (often center, has a border). (c) TOOLBOX zone — selectable options like colors, shapes, actions (often bottom). If you see this layout, your goal is: use the TOOLS to make the WORKSPACE match the REFERENCE. This pattern appeared in sb26 and likely applies to many puzzle games."
- **Expected impact**: Instantly resolves goal blindness on games with this layout. sb26 was solved once this pattern was recognized. Many ARC puzzles use reference-matching mechanics.

### 3. [Exploration] Perform Function Discovery — Test Perform Early With Multiple Hypotheses
- **Hypothesis**: "Perform" means different things in different games: submit answer (sb26), switch active object (re86), activate mechanic, or place/transform. Testing perform EARLY and in DIFFERENT contexts reveals its role, which is critical to understanding the game.
- **Strategy change**: Add to play_strategy.md: "PERFORM DISCOVERY: If 'perform' is available, test it in 3 contexts within your first 10 actions: (a) Perform at start position (does it submit/activate?). (b) Move, then perform (does it do something position-dependent?). (c) Click something, then perform (does it confirm a selection?). Track what perform does — it could mean SUBMIT (sb26), SWITCH CONTROL (re86), PLACE, or TRANSFORM. Knowing which determines your entire strategy."
- **Expected impact**: Both sb26 and re86 required understanding perform's role. In sb26 it submitted the answer; in re86 it switched cross control. Misunderstanding perform wastes many actions.

### 4. [Cross-Game Learning] Level Transition — Carry General Mechanics, Re-Analyze Specifics
- **Hypothesis**: su15 and sb26 both solved level 1 but failed level 2. Level 2 had DIFFERENT specific patterns but the SAME general mechanics. The agent needs to carry forward general knowledge while re-discovering specifics.
- **Strategy change**: Add to play_strategy.md: "LEVEL TRANSITION PROTOCOL: When you advance to a new level: (1) CARRY FORWARD: action types, coordinate system, what perform does, general game mechanic (click-to-paint, move-to-position, etc.). (2) RE-ANALYZE: the specific visual layout — objects may be in different positions, colors may differ, the exact puzzle changes. (3) DON'T assume level 2 is identical to level 1 — it's harder and may introduce new twists. (4) Re-run grid analysis on the new frame BEFORE acting."
- **Expected impact**: Directly addresses the su15 L2 and sb26 L2 failures. General mechanics transfer saves ~10 actions per level. Re-analysis catches changed specifics.

### 5. [Failure Recovery] Minimum Exploration Floor — NEVER Give Up Early
- **Hypothesis**: 8 out of 19 games (42%) had ≤7 actions. lp85 had ZERO. m0r0 had ONE. These are non-attempts. You CANNOT score a game you don't play. This is the single highest-impact change available.
- **Strategy change**: Add to play_strategy.md: "**IRON RULE — MINIMUM 15 ACTIONS**: You MUST take at least 15 actions on every game, no exceptions. If a game confuses you, that's NORMAL — every game is unknown. Use those 15 actions to: (1) Try every available action type. (2) Click on every distinct-looking object. (3) Test movement in all directions. (4) Try perform. (5) Analyze the grid numerically. DO NOT give up because you don't understand the game immediately. Humans don't understand it immediately either — they explore."
- **Expected impact**: Would have directly impacted 8/19 games. Even unfocused exploration over 15 actions has a chance of discovering mechanics. 0 actions has ZERO chance.

### 6. [Visual Analysis] Counter and Header Monitoring
- **Hypothesis**: vc33 and ft09 both noted "clicks decrement counter" but didn't use it as a learning signal. Counters ARE the game's feedback mechanism.
- **Strategy change**: Add to play_strategy.md: "COUNTER RULE: If the frame has numerical indicators, counters, or progress bars — these are your PRIMARY feedback signal. After each action, check: Did the counter change? Test which clicks affect it and which don't."
- **Expected impact**: Directly addresses vc33/ft09 counter blindness.

### 7. [Pattern Recognition] Goal State Inference — "What Does Winning Look Like?"
- **Hypothesis**: Goal blindness is #1 failure (67% of 0-score games). Adding "MATCH a reference" to the win condition checklist was validated by sb26 breakthrough.
- **Strategy change**: Add to play_strategy.md: "GOAL QUESTION: Before your 5th action, answer: 'What does winning look like?' Checklist: (a) REACH a target. (b) COMPLETE a pattern. (c) MATCH a reference. (d) EMPTY a counter. (e) SORT/ALIGN objects. (f) TRANSFORM the grid. (g) POSITION objects to satisfy constraints (re86)."
- **Expected impact**: Prerequisite for scoring. Updated with constraint satisfaction from re86.

### 8. [Exploration] Action Combination Testing
- **Hypothesis**: sb26 required select-then-apply (click color, click dot). re86 required move-then-perform. Multi-step sequences are the NORM, not the exception.
- **Strategy change**: Add to play_strategy.md: "TEST COMBINATIONS: (a) Click object, then perform. (b) Move to position, then perform. (c) Click object A, then click object B. (d) Click selector, then click target. Most games require 2-3 action sequences, not single actions."
- **Expected impact**: Validated by 2/3 breakthroughs. Combinations are the core mechanic in most games.

### 9. [Efficiency] Midpoint Reassessment for High-Engagement Failures
- **Hypothesis**: 5 games used 28-40 actions and scored 0 (bp35, r11l, tu93, wa30, ka59). The agent persists but doesn't convert. At the midpoint of your budget, a forced reassessment could catch wrong hypotheses and redirect remaining actions.
- **Strategy change**: Add to play_strategy.md: "MIDPOINT CHECK (at action 20 of 40): Stop and assess: (1) Do I understand what the goal is? If no — the next 20 actions should focus on goal discovery, not mechanics. (2) Am I closer to solving than at action 1? If no — I'm probably pursuing a wrong model. RESET my understanding and re-examine the frame. (3) Have I tried ALL available action types and combinations? If no — try the ones I haven't. (4) Can I state what perform does in this game? If no — test perform NOW. Don't spend the second half repeating the first half's failures."
- **Expected impact**: Directly targets the 5 high-engagement failures. Forces strategic pivots at the midpoint instead of grinding through 40 actions with a wrong model.

### 10. [Failure Recovery] Stagnation Rule + Reclassification
- **Hypothesis**: 5+ actions with no change = wrong approach. Also, every 10 actions, reassess game type hypothesis.
- **Strategy change**: Add to play_strategy.md: "STAGNATION RULE: 5 actions with no change → switch action type entirely. Every 10 actions → re-examine frame with fresh eyes, question your game type hypothesis."
- **Expected impact**: Forces pivots. Combined stagnation detection with periodic reclassification.

### 11. [Visual Analysis] Structural Grid Analysis
- **Hypothesis**: Dividers, borders, zones define WHERE the game happens. sb26's reference/workspace/toolbox were separated by borders.
- **Strategy change**: Add to play_strategy.md: "Identify STRUCTURAL elements first: borders, dividers, uniform regions. These separate functional zones and tell you WHERE to focus."
- **Expected impact**: Reduces search space. Validated by sb26 zone detection.

### 12. [Hypothesis Testing] Undo-Based Action Survey
- **Hypothesis**: Try each action once with undo to build a complete action-effect map. BUT: undo costs actions (ar25 finding), so adapt if expensive.
- **Strategy change**: Add to play_strategy.md: "Try each available action once. If undo is available and cheap, undo after each to reset. If undo is expensive, accept the state changes and just observe what each action does."
- **Expected impact**: Foundational information gathering. Demoted from #5 since breakthroughs didn't rely on undo survey.

### 13. [Visual Analysis] Frame Differencing + Movement Step Detection
- **Hypothesis**: Compare frames after every action. re86 revealed arrow moves shift by 3px, not 1 — step size detection is critical for movement games.
- **Strategy change**: Add to play_strategy.md: "After each action: what changed? For movement: how FAR did it move? (re86: 3px per arrow). For clicks: what appeared/disappeared? Step size × distance = action count needed."
- **Expected impact**: Catches subtle changes AND enables action planning via step size calculation.

### 14. [Exploration] State Novelty Seeking
- **Hypothesis**: Prioritize actions producing new frames. Avoid cycling through visited states.
- **Strategy change**: Add to play_strategy.md: "NOVELTY RULE: Prioritize actions producing NOVEL frames. If a frame looks familiar, try a different action. Novelty = information."
- **Expected impact**: Anti-cycle strategy from competition winners.

### 15. [Action Prioritization] Click-Target Identification
- **Hypothesis**: Systematic clicking on distinct objects, ordered by visual salience, beats random clicking.
- **Strategy change**: Add to play_strategy.md: "For click games: list all non-background objects by color and position. Click brightest/smallest/most isolated first (likely buttons). Map interactive vs decorative."
- **Expected impact**: Combines old click-target and salience strategies. Validated by su15 approach.

### 16. [Navigation] Systematic Map Building for Movement Games
- **Hypothesis**: Navigation games (ls20, sp80) have 0 wins. The agent moves but has no spatial strategy. Systematic exploration (pick a direction, go until blocked, turn, repeat) builds a mental map that reveals goals, paths, and boundaries. Wall-following is a proven maze-solving heuristic.
- **Strategy change**: Add to play_strategy.md: "NAVIGATION PROTOCOL for movement games: (1) ORIENT: Move one step in each direction to detect walls/boundaries and determine step size. (2) EXPLORE SYSTEMATICALLY: Pick a direction, move until blocked, then turn right (wall-following). This guarantees coverage of connected spaces. (3) TRACK POSITION: Note your position after each move (count steps from start). (4) WATCH FOR LANDMARKS: Different colored cells, special objects, or visual changes = potential goals or interactive points. (5) SCROLL AWARENESS: If the world scrolls (sp80), the map extends beyond your view — keep exploring in one direction to discover new areas. Don't assume the visible frame is the whole world."
- **Expected impact**: Navigation games are 0/15 — the biggest gap. Wall-following alone solves many maze-type games. Position tracking prevents backtracking waste.

### 17. [Strategy] Retry Failed Games — Specific Replay Plan
- **Hypothesis**: Early games were played before breakthroughs. Current strategies are much better. Prioritized replay targets below.
- **Strategy change**: After finishing all 25, replay in this priority order:
  1. **tr87** (3 actions) — symbol tiles. Apply grid parsing + zone detection. Was barely attempted.
  2. **ft09** (5 actions) — pattern grid. Apply grid parsing + counter monitoring. Analogy/XOR patterns need numerical analysis.
  3. **sc25** (5 actions) — barely attempted. Apply full exploration protocol.
  4. **g50t** (5 actions) — barely attempted. Apply full exploration protocol.
  5. **vc33** (7 actions) — counter game. Apply counter monitoring + systematic clicking.
  6. **dc22** (7 actions) — barely attempted. Apply full exploration protocol.
  7. **lp85** (0 actions!) — wasn't even attempted. Must play for real.
  8. **m0r0** (1 action) — wasn't attempted. Must play for real.
  9. **ar25** (16 actions) — multi-mechanic. Apply action combination testing + perform discovery.
  10. **ls20** (16 actions) — navigation. Apply navigation protocol.
- **Expected impact**: The lowest-action games have the most room to improve. Converting even 3-4 of these to scores would nearly double our score count.

---

## Completed

(none yet)
