# Research Notes

Accumulated knowledge from experiments. Never wiped, only appended.

## Fresh Start — 25 Games, Generic Approach

Starting clean with all 25 ARC-AGI-3 games. The goal is to develop strategies
that work across ANY game, not game-specific solutions.

All games are solvable by humans. Every game is a test for AI.

## 2026-03-30: Initial Research — Competition Landscape

### Competition State
- Humans score **100%** on ARC-AGI-3. Frontier AI scores **< 1%**.
- Best AI approach (StochasticGoose, 12.58%) used CNN + RL — not pure LLM.
- Pure LLM approaches scored 3.7-4.4% in ARC-AGI-2 preview.
- The winning approaches used **informed search** — exploring as much of the action space as possible.

### Core AI Weaknesses (from ARC Prize 30-day learnings)
1. **Exploration efficiency** — AI agents waste actions on blind exploration
2. **Hypothesis revision** — agents commit to wrong hypotheses too long
3. **Planning under uncertainty** — agents don't plan before acting
4. **Information-to-strategy conversion** — humans convert observations into strategy much faster

### Scoring Insight
Score = max(0, 1 - (agent_actions / (3 * human_actions))). This means:
- If you use 3x what a human uses, score = 0
- Action efficiency IS the entire game
- Every wasted exploratory action directly hurts score
- Information density per action is the key metric

### Strategy Principles Derived
1. **Maximize information per action** — undo-based surveys give 2 actions worth of info for every action type
2. **Explicit visual differencing** — AI's biggest gap vs humans is visual change detection
3. **Budget exploration** — hard cap exploration time, force transition to execution
4. **Hypothesis falsification > confirmation** — disprove fast, don't confirm slowly
5. **Carry knowledge across levels** — same game mechanics persist, don't re-explore

### Queue Seeded
Populated 14 ideas covering: hypothesis testing, visual analysis, efficiency, pattern recognition, failure recovery, cross-game learning, action prioritization, and exploration. Priority order puts foundational strategies (action survey, frame differencing, budgeting) first.

## Key Insights

- **Information density per action** is the fundamental metric. Every strategy should maximize this.
- **Two-phase approach** (explore then exploit) maps directly to the scoring function.
- **Visual analysis** is the biggest gap between human and AI performance.
- **Hypothesis revision** failure is the #1 cause of wasted actions.

## 2026-03-30: Competition Winner Analysis

### 3rd Place: "Just Explore" (Graph-Based Explorer)
- **Training-free** — no ML, no LLM. Pure structured exploration.
- Segments frames into single-color connected components
- Maintains directed graph: nodes = states, edges = actions
- **5-tier action priority** based on visual salience (size, color, morphology)
- Solved **17/25 median levels** (one below 1st place!)
- Key insight: **prioritized action exploration beats random search AND LLM reasoning**
- Weakness: degrades on massive state spaces and when status bars confuse hashing

### 1st Place: StochasticGoose (CNN + RL)
- CNN predicts which actions cause frame changes
- 4-layer convolutional network on 64x64 frames
- Completed 18 levels — only 1 more than the graph-based approach
- Both winning approaches = **informed search** of action space

### Implication for Our Strategies
The top approaches all share three traits:
1. **State tracking** — know where you've been, avoid cycles
2. **Visual salience** — focus on likely-interactive elements first
3. **Systematic coverage** — explore all actions at high-priority targets before moving to low-priority

These map directly to queue items #15 (novelty seeking), #16 (salience prioritization), and #17 (transition mapping). These should be high-priority additions to the play strategy.

## 2026-03-30: Game Archetypes & Learning Gap Analysis

### Three Game Archetypes (from ARC Prize 30-day report)
1. **Agentic / Map-based** (e.g., ls20): Navigate a map, move objects, transform things at locations. Movement-heavy, spatial reasoning required.
2. **Non-agentic / Logic** (e.g., ft09): Pattern matching, no avatar to control. Click or perform to manipulate the grid directly. Visual reasoning dominates.
3. **Orchestration** (e.g., vc33): Multiple objects to manipulate simultaneously. Requires understanding relationships between objects and coordinating actions.

### The Real Gap: Learning From Exploration
ARC Prize data shows AI exhibits "persistent inefficiency even after environmental interaction." This means:
- AI explores but **doesn't convert observations into usable strategy**
- Humans show clear learning curves; AI doesn't
- The problem isn't WHAT to explore, but HOW TO LEARN from exploration

### Strategy Implications
This shifts priority toward **learning-from-exploration** strategies:
- **#2 (Frame differencing)** — forces explicit observation recording
- **#6 (Level transition capture)** — forces knowledge carry-forward
- **#17 (Transition mapping)** — forces structured learning
- **#15 (State novelty)** — avoids repeating what you already know

These four should be tested early alongside #1 (action survey). Together they form a "systematic discovery protocol" — explore systematically AND record what you learn.

### 2nd Place: "Blind Squirrel" (State Graph + Pruning)
- Built state graphs (like 3rd place)
- Additionally **pruned non-productive actions** — actions that never cause change get dropped
- Retrained value models during exploration
- Score: 6.71%
- Key lesson: pruning dead-end actions is as important as finding productive ones

### Coverage Assessment of Current Queue
| Archetype | Well-covered? | Key queue items |
|-----------|--------------|----------------|
| Agentic/Navigation | Yes | #1, #11, #13, #15, #17 |
| Pattern/Logic | Moderate | #2, #4, #9, #12 |
| Orchestration | Weakest | #12, #16 |

Orchestration games (multi-object coordination) are least covered. May need targeted strategies if these prove to be failure points.

## 2026-03-30: First Results Analysis (Exp 001-006)

### Results Summary
ALL 6 games scored 0. Total actions used: 69 out of ~240 possible (40 per game). Agent is drastically underusing its action budget.

### Failure Pattern Analysis

| Pattern | Games | Frequency | Impact |
|---------|-------|-----------|--------|
| Goal blindness | ls20, sp80, ar25, tr87 | 4/6 (67%) | Can't score without knowing what winning is |
| Counter/indicator blindness | vc33, ft09 | 2/6 (33%) | Feedback signal exists but is ignored |
| Premature surrender | tr87 (3 acts), ft09 (5 acts) | 2/6 (33%) | Wastes most of action budget |
| Movement-only focus | sp80 (22 acts, 0 score) | 1/6 (17%) | Keeps moving but never pivots strategy |
| Multi-mechanic overwhelm | ar25 | 1/6 (17%) | Too many action types to figure out |

### Key Insight: Agent Underexplores
Average actions per game: 11.5. With 40 actions available, the agent is using only **29%** of its budget. The agent is TOO CONSERVATIVE with exploration — it gives up rather than continuing to try things.

This is the OPPOSITE of the failure mode I predicted (endless exploration). The real problem is:
1. Agent doesn't explore ENOUGH
2. Agent doesn't know what WINNING looks like
3. Agent ignores feedback signals (counters)
4. Agent doesn't test action combinations

### Queue Reprioritization
Promoted to top 3:
- **#1**: Minimum exploration floor (15 actions) — fixes premature surrender
- **#2**: Counter/header monitoring — fixes feedback blindness
- **#3**: Goal state inference — fixes goal blindness

Demoted (still important but not the primary bottleneck):
- Undo-based survey → #4
- Frame differencing → #5

Added new:
- **#6**: Action combination testing — addresses multi-mechanic games like ar25

### Game-Specific Observations (for pattern matching, NOT game-specific strategies)
- **ls20**: Sliding block → navigation archetype. Movement works but goal unknown.
- **vc33**: Click-only with counter → orchestration archetype. Counter IS the puzzle.
- **ft09**: 4-quadrant pattern → logic archetype. Analogy/pattern completion likely.
- **ar25**: Movement + perform + click → complex archetype. Dividers = structural boundaries.
- **sp80**: Platformer with scrolling → navigation archetype. Large world beyond visible frame.
- **tr87**: Symbol tiles → logic archetype. Agent gave up after 3 actions (too complex visually).

## Dead Ends

(patterns that don't work — to be filled as experiments run)
