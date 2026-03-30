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

## Dead Ends

(patterns that don't work — to be filled as experiments run)
