# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**Priority rationale**: Top items (#1-5) form a "Systematic Discovery Protocol" — they address the core AI weakness of failing to learn from exploration. Items #6-10 add efficiency and failure recovery. Items #11-17 are advanced pattern recognition and specialist strategies.

---

### 1. [Hypothesis Testing] Undo-Based Action Survey
- **Hypothesis**: The biggest information bottleneck is not knowing what each action does. A systematic survey using undo to reset between tries gives maximum information per action cost.
- **Strategy change**: Add to play_strategy.md: "Before doing anything else, try each available action exactly once, using undo after each. Record what changed. This costs 2 actions per action type (~14 actions total for 7 action types) but gives you a complete action-effect map."
- **Expected impact**: Eliminates blind guessing across all game types. Every subsequent action is informed rather than exploratory.

### 2. [Visual Analysis] Explicit Frame Differencing
- **Hypothesis**: AI agents often gloss over visual changes. Forcing explicit before/after comparison after every action catches subtle changes humans notice instantly.
- **Strategy change**: Add to play_strategy.md: "After EVERY action, compare the new frame to the previous one. Ask: What pixels/cells changed? What color did they become? Did anything appear/disappear? Did anything move? Describe the change in one sentence before choosing your next action."
- **Expected impact**: Catches subtle feedback the agent currently misses — small score indicators, single-cell changes, border highlights. Helps across all 25 games.

### 3. [Efficiency] Two-Phase Budget System
- **Hypothesis**: Agents waste actions by mixing exploration and execution. A clear budget forces the transition from learning to solving.
- **Strategy change**: Add to play_strategy.md: "Split your actions into two explicit phases. Phase 1 (EXPLORE): Spend the first 25% of your action budget discovering what each action does and what the goal is. Phase 2 (EXECUTE): Spend the remaining 75% applying what you learned. When you enter Phase 2, STOP exploring and focus on efficient execution."
- **Expected impact**: Prevents the common failure mode of endless exploration. Competition data shows efficiency is the scoring mechanism — action economy matters.

### 4. [Pattern Recognition] Goal State Inference from Visual Cues
- **Hypothesis**: Many ARC games embed the goal visually — incomplete patterns, asymmetries, highlighted targets. Training the agent to look for these before acting reduces wasted exploration.
- **Strategy change**: Add to play_strategy.md: "Before taking any action, analyze the frame for goal cues: (a) Is there an incomplete pattern that needs completing? (b) Are there two similar regions where one looks 'finished' and the other doesn't? (c) Is there a highlighted/colored target area? (d) Does the layout suggest a before/after comparison? Formulate a goal hypothesis BEFORE your first action."
- **Expected impact**: Reduces exploration overhead on games where the goal is visually apparent. Humans do this instantly — they look before they leap.

### 5. [Failure Recovery] Five-Action Stagnation Rule
- **Hypothesis**: Agents get stuck repeating ineffective actions. A hard cutoff forces strategy switches and prevents action waste.
- **Strategy change**: Add to play_strategy.md: "STAGNATION RULE: If 5 consecutive actions produce no visible frame change and no score change, you are doing the wrong thing. Immediately: (1) Stop current approach. (2) Try a completely different action type. (3) If you were moving, try clicking. If clicking, try movement. If both, try perform. (4) Target a different region of the grid."
- **Expected impact**: Prevents the #1 failure mode observed in AI agents: repeating ineffective actions. Forces exploration of alternative mechanics.

### 6. [Cross-Game Learning] Level Transition Knowledge Capture
- **Hypothesis**: When advancing to a new level, agents forget what they learned. Explicitly carrying forward game mechanics saves re-exploration actions.
- **Strategy change**: Add to play_strategy.md: "When you complete a level (GAME_OVER with score > 0), BEFORE starting the next level, write down: (1) What each action does in this game. (2) What the goal was. (3) What sequence solved it. Then apply this knowledge immediately to the next level — skip re-exploration and go straight to execution."
- **Expected impact**: Levels in the same game share mechanics. Re-discovering them wastes 10-20 actions per level. This compounds across multi-level games.

### 7. [Action Prioritization] Click-Target Identification for Click Games
- **Hypothesis**: In click-based games, random clicking wastes many actions. Systematically identifying visually distinct objects and clicking them in order is far more efficient.
- **Strategy change**: Add to play_strategy.md: "For games with click actions: (1) Identify all visually distinct objects (different colors, shapes, or patterns from background). (2) Click each one systematically, starting from top-left, moving right then down. (3) After each click, check if anything changed. (4) Build a map of which objects are interactive vs decorative."
- **Expected impact**: Click games are common in ARC-AGI-3. Systematic targeting vs random clicking could reduce actions by 50%+ on these games.

### 8. [Hypothesis Testing] Falsification Over Confirmation
- **Hypothesis**: Agents tend to confirm their first hypothesis rather than testing alternatives. Deliberately falsifying hypotheses leads to faster convergence on correct understanding.
- **Strategy change**: Add to play_strategy.md: "When you form a hypothesis about how the game works, your NEXT action should try to DISPROVE it, not confirm it. Example: If you think 'clicking blue things is the goal,' click a non-blue thing to see what happens. If your hypothesis survives falsification, it's more likely correct. If it fails, you've saved many wasted actions."
- **Expected impact**: Faster convergence to correct game understanding. Prevents the costly failure mode of committing to a wrong hypothesis for many actions.

### 9. [Visual Analysis] Structural Grid Analysis
- **Hypothesis**: Many ARC games have structural elements (dividers, borders, zones) that define the playing field. Identifying these first narrows the search space.
- **Strategy change**: Add to play_strategy.md: "In your initial observation, identify STRUCTURAL elements: (a) Solid lines/borders that divide the grid into zones. (b) Uniform colored regions (likely background, not interactive). (c) Grid-within-grid patterns. (d) Repeating elements vs unique elements. Structural elements tell you WHERE the game happens. Focus your actions on the non-structural areas."
- **Expected impact**: Reduces the clickable/movable search space significantly. Structural analysis is something humans do unconsciously but AI agents skip.

### 10. [Efficiency] Minimize Resets — Plan Before Resetting
- **Hypothesis**: Resets cost an action and lose all progress. Agents reset too eagerly when stuck instead of trying alternative approaches.
- **Strategy change**: Add to play_strategy.md: "RESET RULE: Never reset unless you have BOTH: (1) A clear reason the current state is unrecoverable, AND (2) A new strategy to try after resetting. Resetting without a new plan just repeats the same failure. Prefer undo (reverses one step) over reset (loses everything) when possible."
- **Expected impact**: Saves 1+ actions per game on average. Resets are the most expensive "do nothing" action since they waste all prior progress.

### 11. [Exploration] Boundary and Corner Testing
- **Hypothesis**: Game boundaries often reveal mechanics — walls, wrapping, teleportation, or boundary-triggered effects. Testing edges early reveals the game's spatial rules.
- **Strategy change**: Add to play_strategy.md: "During exploration phase, test boundaries: (a) Move to each edge of the grid and see what happens. (b) Click on corner cells. (c) Try to move past boundaries — does it wrap, block, or trigger something? This reveals the game's spatial model efficiently."
- **Expected impact**: Spatial rules are fundamental to many games. Understanding boundaries early prevents wasted actions bumping into walls or missing wrap-around mechanics.

### 12. [Pattern Recognition] Multi-Object Relationship Detection
- **Hypothesis**: Many games involve relationships between objects (matching colors, mirroring positions, connecting dots). Detecting these relationships early reveals the game's logic.
- **Strategy change**: Add to play_strategy.md: "After initial observation, ask: (a) Are there pairs of objects with the same color/shape? (b) Is there a spatial pattern (symmetry, alignment, grouping)? (c) Do objects seem to have a one-to-one correspondence? (d) Is there a source-target relationship? Relationship detection often reveals the goal faster than trial-and-error."
- **Expected impact**: Many ARC puzzles are relationship-based. Detecting the relationship IS solving half the puzzle. Works across matching, sorting, connecting, and mirroring game types.

### 13. [Action Prioritization] Perform-First Heuristic
- **Hypothesis**: The "perform" action is often the key mechanic but agents try it last. Testing perform early on different objects could reveal the core game loop faster.
- **Strategy change**: Add to play_strategy.md: "If 'perform' is available, try it EARLY — before extensive movement or clicking. Perform often triggers the main game mechanic (placing, activating, transforming). Try perform in your initial state, then after moving to different positions. Perform + position combinations are often the core of the game."
- **Expected impact**: Perform is underexplored by most agents who default to movement. Many games require perform as the primary action.

### 14. [Failure Recovery] Game Type Reclassification
- **Hypothesis**: When an agent's initial game type classification is wrong, all subsequent actions are wasted. Forcing periodic reclassification catches these errors.
- **Strategy change**: Add to play_strategy.md: "Every 10 actions, reassess: Is your game type hypothesis still correct? If you've taken 10 actions with no progress, your classification is probably wrong. Re-examine the frame with fresh eyes: What if it's NOT a navigation game? What if clicking IS the mechanic? What if the goal is different from what you assumed?"
- **Expected impact**: Prevents sustained commitment to wrong approaches. The periodic check costs nothing (it's just thinking) but can save dozens of wasted actions.

### 15. [Exploration] State Novelty Seeking — Prioritize New Frames
- **Hypothesis**: The 3rd-place competition solution (graph-based explorer) succeeded by tracking visited states and prioritizing actions that lead to NEW states. An LLM agent can do the same by comparing frames: if an action produces a frame you've seen before, deprioritize that action path.
- **Strategy change**: Add to play_strategy.md: "NOVELTY RULE: After each action, ask: Have I seen this frame before? If the frame looks identical to a previous state, you're going in circles. Prioritize actions that produce NOVEL frames — new arrangements, new colors, new object positions. Novelty = information. Repetition = waste."
- **Expected impact**: Directly addresses the #1 failure mode from competition data: agents cycling through visited states. The winning approaches all had state-tracking to avoid this.

### 16. [Visual Analysis] Visual Salience Prioritization
- **Hypothesis**: Competition winner's key insight: not all objects are equally likely to be interactive. Small, brightly-colored, isolated objects are far more likely to be buttons/toggles than large uniform regions. Prioritizing by visual salience dramatically reduces wasted clicks.
- **Strategy change**: Add to play_strategy.md: "SALIENCE RULE for click games: Rank clickable objects by visual salience. Highest priority: small, brightly colored, isolated objects (likely buttons). Medium: objects that differ from their neighbors. Lowest: large uniform regions (likely background). Click in salience order, not spatial order."
- **Expected impact**: The 3rd-place solution used this as its core heuristic and solved 17/25 levels. Visual salience is a strong prior for interactivity in puzzle games.

### 17. [Exploration] Action-Effect Transition Mapping
- **Hypothesis**: Building an explicit mental map of "in state A, action X leads to state B" allows planning multi-step solutions instead of one-step guessing. This is what the graph-based approaches do programmatically.
- **Strategy change**: Add to play_strategy.md: "BUILD A TRANSITION MAP: As you explore, explicitly track: 'From [state description], action [X] caused [effect] and led to [new state].' After 5-10 actions, you should have a partial map of the game's state space. Use this map to PLAN sequences of actions to reach unexplored or desirable states, rather than trying actions one at a time."
- **Expected impact**: Transforms exploration from memoryless trial-and-error into informed search. The top 3 competition solutions all used explicit state-transition tracking.

---

## Completed

(none yet)
