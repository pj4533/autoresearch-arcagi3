# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**Priority rationale (updated after Exp 010-013 — 3 BREAKTHROUGHS)**: su15, sb26, re86 all scored 1. Common thread: mathematical grid analysis + multi-step action sequences + reference/target identification. 3/13 games scoring (23%). Level 2 failures on su15 and sb26 highlight need for level transition strategies.

> **WHAT WORKS (3 wins)**: Mathematical grid parsing, reference-workspace-toolbox layout detection, constraint satisfaction for positioning, multi-step action sequences (select→apply, move→perform). Grid coordinates are the key data source.
>
> **WHAT STILL FAILS**: Premature surrender (sc25=5 acts), 10/13 games at 0, level 2 failures on solved games, navigation/platformer games (sp80, ls20).

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

### 5. [Failure Recovery] Minimum Exploration Floor — Never Give Up Early
- **Hypothesis**: Exp 006 (tr87) took only 3 actions, Exp 003 (ft09) only 5. This is far too few. A minimum action floor prevents premature surrender.
- **Strategy change**: Add to play_strategy.md: "MINIMUM EXPLORATION RULE: You MUST take at least 15 actions per game before concluding you can't solve it. Use the first 10-15 actions to systematically try every available action type and observe results."
- **Expected impact**: Fixes premature surrender (sc25=5 actions still happening). 4/13 games used <8 actions.

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

### 9. [Efficiency] Two-Phase Budget System
- **Hypothesis**: Clear explore/execute split prevents endless exploration. Data shows 30% explore / 70% execute is about right.
- **Strategy change**: Add to play_strategy.md: "Phase 1 (EXPLORE, ~30%): Map actions, identify goal, test combinations. Phase 2 (EXECUTE, ~70%): Apply what you learned efficiently."
- **Expected impact**: Structure for action budgeting. Breakthroughs all switched cleanly from explore to execute.

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

---

## Completed

(none yet)
