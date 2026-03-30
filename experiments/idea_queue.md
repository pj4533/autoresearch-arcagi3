# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**Priority rationale (updated after Exp 010 BREAKTHROUGH)**: su15 scored 1 — first non-zero! Key success factors: mathematical grid analysis, path identification, sequential clicking, coordinate calibration. Reprioritized to amplify what WORKED. Top items now generalize the su15 success pattern to other games.

> **WHAT WORKED (su15)**: Analyzing grid data numerically (not just visually), identifying spatial paths/connections between objects, clicking sequentially along identified paths. The 0-127→64x64 coordinate mapping was critical.
>
> **WHAT STILL FAILS**: Premature surrender (sc25=5 actions), goal blindness on non-click games. 10/11 games still at 0.

---

### 1. [Visual Analysis] Mathematical Grid Parsing — Use Numbers, Not Just Eyes
- **Hypothesis**: The su15 breakthrough came from analyzing the grid DATA numerically — finding precise pixel coordinates, computing distances between objects, identifying mathematical patterns (e.g., dots at +2 cols, -2 rows each). This is something an LLM can do that pure vision can't. Generalizing this approach to all games could unlock more scoring.
- **Strategy change**: Add to play_strategy.md: "GRID ANALYSIS RULE: Don't just LOOK at the frame — ANALYZE it numerically. After `arc state --image`, also examine the raw grid data. (a) List all non-background pixels by color and exact (row, col) position. (b) Look for mathematical relationships: equally-spaced objects, diagonal lines, symmetry axes, paired objects at mirror positions. (c) Compute distances between similar-colored objects. (d) Identify paths, lines, or connections between objects. This numerical analysis revealed the solution in su15 and is likely the key to many click-based games."
- **Expected impact**: Directly generalizes what worked in the first scored game. Mathematical patterns are invisible to casual visual inspection but obvious to numerical analysis. High probability of unlocking click-based games (vc33, ft09, tr87).

### 2. [Failure Recovery] Minimum Exploration Floor — Never Give Up Early
- **Hypothesis**: Exp 006 (tr87) took only 3 actions, Exp 003 (ft09) only 5. This is far too few to learn anything about an unknown game. A minimum action floor prevents premature surrender.
- **Strategy change**: Add to play_strategy.md: "MINIMUM EXPLORATION RULE: You MUST take at least 15 actions per game before concluding you can't solve it. Use the first 10-15 actions to systematically try every available action type and observe results. Games are solvable by humans — if you haven't figured it out, you haven't explored enough, not that it's unsolvable."
- **Expected impact**: Directly fixes the worst failure mode — giving up after 3-5 actions. Exp 006 had 37 unused actions. Even random exploration with 37 more actions would have been more informative.

### 3. [Visual Analysis] Counter and Header Monitoring
- **Hypothesis**: Exp 002 (vc33) and Exp 003 (ft09) both noted "clicks decrement counter" but the agent didn't use this as a learning signal. Counters/headers ARE the game's feedback mechanism — they tell you whether your actions are productive.
- **Strategy change**: Add to play_strategy.md: "COUNTER RULE: If the frame has any numerical indicators, counters, progress bars, or header text — these are your PRIMARY feedback signal. After each action, check: Did the counter go up, down, or stay the same? A counter going DOWN after a click might mean: (a) you have limited actions remaining, (b) you're solving the puzzle (countdown to win), or (c) you're making the wrong move. Test which by: clicking different objects and seeing which ones change the counter vs which don't."
- **Expected impact**: Directly addresses failures in vc33 and ft09 where counters were noticed but not interpreted. Counter interpretation = understanding the game's feedback loop.

### 4. [Pattern Recognition] Goal State Inference — "What Does Winning Look Like?"
- **Hypothesis**: Exp 001 (ls20) "couldn't figure out goal," Exp 005 (sp80) "no scoring," Exp 007 (bp35) 40 actions with 0 score. The agent explores mechanics but never identifies the win condition. Without a goal, even 40 actions are wasted.
- **Strategy change**: Add to play_strategy.md: "GOAL QUESTION: Before your 5th action, explicitly answer: 'What do I think winning looks like in this game?' Use this checklist of common ARC-AGI-3 win conditions: (a) REACH a target location (colored marker, special cell). (b) COMPLETE a pattern (fill gaps, extend sequence). (c) MATCH a reference (one part of the screen shows the target, you make another part match). (d) EMPTY a counter (counter counts down to 0 = win). (e) SORT/ALIGN objects (put things in order, match colors). (f) TRANSFORM the grid (change it to match a shown goal). If you can't hypothesize a goal after 10 actions, RESET your mental model — you're likely misreading the frame. Look again at what's on screen as if for the first time."
- **Expected impact**: Goal identification is prerequisite for scoring. Expanded checklist with 6 specific win condition types derived from ARC game archetypes. Would have helped on 5/8 games so far.

### 5. [Hypothesis Testing] Undo-Based Action Survey
- **Hypothesis**: The biggest information bottleneck is not knowing what each action does. A systematic survey using undo to reset between tries gives maximum information per action cost.
- **Strategy change**: Add to play_strategy.md: "Before doing anything else, try each available action exactly once, using undo after each. Record what changed. This costs 2 actions per action type (~14 actions total for 7 action types) but gives you a complete action-effect map."
- **Expected impact**: Eliminates blind guessing across all game types. Would have helped on all 6 attempted games. Note: Exp 004 (ar25) found "undo costs actions" — if undo is expensive, do the survey WITHOUT undo and just accept the state changes.

### 6. [Visual Analysis] Explicit Frame Differencing
- **Hypothesis**: AI agents often gloss over visual changes. Exp 002 noted "no visible cell changes" but counter DID change — meaning something subtle changed that was missed.
- **Strategy change**: Add to play_strategy.md: "After EVERY action, compare the new frame to the previous one. Ask: What pixels/cells changed? What color did they become? Did anything appear/disappear? Did anything move? Did any counter/number change? Describe the change in one sentence before choosing your next action."
- **Expected impact**: Would have caught the counter changes in vc33/ft09. Also catches subtle cell changes the agent may have missed.

### 7. [Exploration] Action Combination Testing
- **Hypothesis**: Exp 004 (ar25) had movement + perform + click. Many games require COMBINATIONS of actions (move to position, THEN perform; or click object, THEN move). Testing combinations reveals mechanics that individual actions don't.
- **Strategy change**: Add to play_strategy.md: "After mapping individual actions, test COMBINATIONS: (a) Move to an object, then perform. (b) Click an object, then move. (c) Move to different positions and perform at each. (d) Click multiple objects in sequence. Many games require 2-3 action sequences to trigger effects. Single actions alone may do nothing."
- **Expected impact**: Directly addresses ar25 and similar multi-mechanic games. Combinations are the hidden mechanic in complex games.

### 8. [Efficiency] Two-Phase Budget System
- **Hypothesis**: Agents waste actions by mixing exploration and execution. A clear budget forces the transition from learning to solving.
- **Strategy change**: Add to play_strategy.md: "Split your actions into two explicit phases. Phase 1 (EXPLORE): Spend the first 30% of your action budget (e.g., 12 out of 40 actions) discovering what each action does and what the goal is. Phase 2 (EXECUTE): Spend the remaining 70% applying what you learned. When you enter Phase 2, STOP exploring and focus on efficient execution."
- **Expected impact**: Prevents endless exploration without execution. Updated budget to 30/70 based on observed data — agents need slightly more exploration time than originally estimated.

### 9. [Failure Recovery] Five-Action Stagnation Rule
- **Hypothesis**: Agents get stuck repeating ineffective actions. A hard cutoff forces strategy switches.
- **Strategy change**: Add to play_strategy.md: "STAGNATION RULE: If 5 consecutive actions produce no visible frame change and no score change, you are doing the wrong thing. Immediately: (1) Stop current approach. (2) Try a completely different action type. (3) If you were moving, try clicking. If clicking, try movement. If both, try perform. (4) Target a different region of the grid."
- **Expected impact**: Prevents the #1 failure mode: repeating ineffective actions. Exp 005 (sp80) used 22 actions with 0 score — stagnation detection would have forced an earlier pivot.

### 10. [Visual Analysis] Structural Grid Analysis
- **Hypothesis**: Many ARC games have structural elements (dividers, borders, zones). Exp 004 (ar25) "can't cross divider" — identifying structural elements tells you WHERE the game happens.
- **Strategy change**: Add to play_strategy.md: "In your initial observation, identify STRUCTURAL elements: (a) Solid lines/borders that divide the grid into zones. (b) Uniform colored regions (likely background, not interactive). (c) Grid-within-grid patterns. (d) Repeating elements vs unique elements. Structural elements tell you WHERE the game happens. Focus your actions on the non-structural areas."
- **Expected impact**: Would have helped on ar25 (divider identification) and ft09 (quadrant identification). Reduces search space.

### 11. [Cross-Game Learning] Level Transition Knowledge Capture
- **Hypothesis**: When advancing to a new level, agents forget what they learned. Carrying forward game mechanics saves re-exploration actions.
- **Strategy change**: Add to play_strategy.md: "When you complete a level, BEFORE starting the next level, write down: (1) What each action does. (2) What the goal was. (3) What sequence solved it. Apply this immediately to the next level — skip re-exploration."
- **Expected impact**: Compounds savings across multi-level games. Not yet relevant (no levels solved) but will be critical once scoring starts.

### 12. [Action Prioritization] Click-Target Identification for Click Games
- **Hypothesis**: Exp 002 (vc33) and Exp 003 (ft09) are click-only games where random clicking wastes actions.
- **Strategy change**: Add to play_strategy.md: "For click games: (1) Identify all visually distinct objects. (2) Click each systematically. (3) After each click, check counter/frame changes. (4) Map which objects are interactive vs decorative. (5) Focus subsequent clicks on interactive objects only."
- **Expected impact**: Would reduce wasted actions in vc33, ft09, and other click-based games.

### 13. [Hypothesis Testing] Falsification Over Confirmation
- **Hypothesis**: Agents confirm their first hypothesis rather than testing alternatives. Deliberately falsifying leads to faster convergence.
- **Strategy change**: Add to play_strategy.md: "When you form a hypothesis, your NEXT action should try to DISPROVE it. If your hypothesis survives falsification, it's more likely correct."
- **Expected impact**: Faster convergence to correct game understanding. Prevents committing to wrong hypotheses.

### 14. [Action Prioritization] Perform-First Heuristic
- **Hypothesis**: "Perform" is often the key mechanic but agents try it last. Exp 004 (ar25) has perform available but notes suggest movement was tried first.
- **Strategy change**: Add to play_strategy.md: "If 'perform' is available, try it EARLY — before extensive movement or clicking. Perform often triggers the main game mechanic. Try perform at your starting position, then after moving to different spots."
- **Expected impact**: Many games require perform as the primary action. Testing it early reveals the core game loop.

### 15. [Exploration] State Novelty Seeking — Prioritize New Frames
- **Hypothesis**: Track visited states to avoid cycles. Prioritize actions producing novel frames.
- **Strategy change**: Add to play_strategy.md: "NOVELTY RULE: After each action, ask: Have I seen this frame before? Prioritize actions that produce NOVEL frames. Novelty = information. Repetition = waste."
- **Expected impact**: Avoids cycling through visited states — the #1 failure in competition data.

### 16. [Visual Analysis] Visual Salience Prioritization
- **Hypothesis**: Not all objects are equally interactive. Small, bright, isolated objects are most likely to be buttons/toggles.
- **Strategy change**: Add to play_strategy.md: "SALIENCE RULE: Rank clickable objects by visual salience. Highest priority: small, brightly colored, isolated objects (likely buttons). Lowest: large uniform regions (likely background)."
- **Expected impact**: Competition winner's core heuristic (17/25 levels solved).

### 17. [Failure Recovery] Game Type Reclassification
- **Hypothesis**: Wrong initial classification wastes all subsequent actions. Exp 003 (ft09) "Analogy puzzle? XOR pattern?" — uncertainty in classification led to inaction.
- **Strategy change**: Add to play_strategy.md: "Every 10 actions, reassess your game type hypothesis. If no progress, your classification is probably wrong. Re-examine with fresh eyes."
- **Expected impact**: Catches wrong assumptions early, especially for ambiguous games like ft09.

### 18. [Exploration] Action-Effect Transition Mapping
- **Hypothesis**: Explicit state-transition maps enable multi-step planning instead of one-step guessing.
- **Strategy change**: Add to play_strategy.md: "BUILD A TRANSITION MAP: Track 'From [state], action [X] → [new state].' Use this map to PLAN sequences rather than guessing."
- **Expected impact**: Top 3 competition solutions all used explicit state-transition tracking.

---

## Completed

(none yet)
