# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 014): 14 stategraph experiments + 30 explorer experiments = 44 total, ALL score 0. Programmatic exploration can't solve puzzles (needs sequence reasoning). Qwen3.5 can't reason about grids (exps 012-013). Game code analysis doesn't generalize to instances (exp 014). CRITICAL: We still don't know if the framework itself works. Cloud model validation with Claude Sonnet is THE gating experiment — everything else is premature until we know if scoring is possible.**

**CORRECTION: My earlier analysis that color 9 = "corrupting/ZGd" and color 1 = "winning/zHk" was WRONG. Each game instance has different color mappings. Color 9 IS the interactive color in this instance (confirmed by 265 cell changes). The game code analysis of sprite tags doesn't map to specific instance colors.**

---

### 1. [Architecture] Cloud model validation — MUST RUN BEFORE ANYTHING ELSE
- **Hypothesis**: After 44 experiments scoring 0, the most important unknown is: CAN any agent score on these games through our framework? Claude Sonnet 4.5 with thinking is one of the strongest reasoning models available. If it scores > 0 on even ONE game, we know: (a) the framework works, (b) the bottleneck is model intelligence, (c) we should invest in better models or code-generation approaches. If Claude ALSO scores 0, we know: (a) there may be a framework bug, or (b) the games are fundamentally too hard for LLM-per-step approaches at 40 actions.
- **Files to modify**: None — CLI args only
- **Changes**: Run exactly this command:
  ```bash
  uv run python run_benchmark.py --agent explorer --config claude-sonnet-4-5-20250929-thinking-8k --max-actions 40 --games vc33-9851e02b
  ```
  This runs the explorer agent with Claude Sonnet 4.5 (thinking, 8k budget) on vc33 only. Expected cost: $0.50-$2.00. Expected time: 5-15 minutes.

  **If Claude can't be used** (e.g., no ANTHROPIC_API_KEY), try any available cloud model:
  - `claude-sonnet-4-5-20250929` (no thinking, cheaper)
  - Any OpenAI or Gemini config from models.yml
  - Check available configs: `uv run python -m arcagi3.runner --list-models`
- **Expected impact**: Determines the ENTIRE strategic direction for all future experiments.

### 2. [Architecture] Cloud model on LS20 — validate movement game too
- **Hypothesis**: If cloud validation on vc33 reveals the framework works, also validate ls20. LS20 is a movement game where the state space is enormous but a strong model might reason about navigation. If Claude scores on ls20, the path forward is clear: better reasoning.
- **Files to modify**: None — CLI args only
- **Changes**: `uv run python run_benchmark.py --agent explorer --config claude-sonnet-4-5-20250929-thinking-8k --max-actions 40 --games ls20-cb3b57cc`
- **Expected impact**: Validates ls20 scoring potential with a strong model.

### 3. [Architecture] Code-generation approach (Symbolica-style)
- **Hypothesis**: Symbolica scored 36.08% by having LLM write Python code. Our LLM-per-step approach failed because Qwen3.5 can't reason well enough per step. But a strong cloud model (Claude Sonnet) generating a STRATEGY FUNCTION once can guide many actions. The function analyzes the grid and decides what to click/where to move.
- **Files to modify**: New agent or stategraph modification
- **Changes**: At step 0, call Claude Sonnet with grid + available actions. Ask it to write `def choose_action(grid, available_actions, history) -> dict`. Execute the function for all subsequent steps. Re-call if stuck.
- **Expected impact**: Cloud model intelligence for strategy, zero per-action cost after initial call.

### 4. [Exploration Strategy] VC33 sequential click learning — observe effects and adapt
- **Hypothesis**: Exp 011 showed the agent finds interactive objects but "can't solve the puzzle SEQUENCE." The agent needs to observe the EFFECT of each click and use that to decide the NEXT click. Instead of clicking all targets once, click one target, observe the effect, and reason about what changed. This is sequential decision-making, not batch exploration.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Click ONE interactive object (color that produces most cell changes)
  2. After clicking, analyze what changed: which cells changed color? What pattern emerged?
  3. Based on the change pattern, decide next click: if the change was "cells moved toward a goal area", click the SAME object again. If "cells filled in a row", look for the next unfilled area.
  4. Build a simple rule: "click X until pattern Y appears, then click Z"
  5. This is a feedback loop: click → observe → decide → click
- **Expected impact**: Sequential reasoning instead of batch exploration. Even without LLM, observing effects and adapting is smarter than brute-force.

### 5. [Exploration Strategy] VC33 click repetition — try clicking same object multiple times
- **Hypothesis**: Many puzzle games require clicking the same button multiple times (toggling states, incrementing values, adjusting positions). The stategraph marks each (state, action) pair as "tried" and never repeats it. But for vc33 "volume/height adjustment", clicking the same object N times may be the solution (adjust height to target). Try clicking each interactive object 1-10 times in sequence.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: For vc33 (click-only game): don't mark click actions as "tried" after one attempt. Instead, allow clicking the same object up to N times (e.g., 10). Track how many times each object has been clicked and the cumulative effect.
- **Expected impact**: If vc33 requires repeated clicking (like adjusting a slider), this is essential.

### 6. [Exploration Strategy] VC33 systematic combination search — try all 2-3 click combos
- **Hypothesis**: If vc33 level 1 needs 6 clicks and there are ~5-10 interactive objects, the search space for 2-3 click sequences is manageable: C(10,2)=45 pairs, C(10,3)=120 triples. Try all short click sequences systematically.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Enumerate all pairs and triples of interactive objects. For each combination, click them in sequence and check for score increase. Reset (if possible) between attempts.
- **Expected impact**: Exhaustive search of short sequences. With 50 lives, can try ~15-25 different 2-3 click combos.

### 7. [Architecture] Manual game play — human plays vc33 to understand mechanics
- **Hypothesis**: After 44 experiments, nobody has manually played these games. Playing vc33 manually (using arc CLI) for 5 minutes would reveal: what do the interactive objects do? What's the goal? What does a winning sequence look like? This insight is worth more than 10 automated experiments.
- **Files to modify**: None — manual exploration
- **Changes**: Start a vc33 session:
  ```bash
  arc start vc33 --max-actions 50
  arc state --image    # See the grid
  # Click various objects and observe
  arc action click --x 60 --y 24
  arc state --image    # What changed?
  arc action click --x 60 --y 32
  arc state --image
  # ... experiment with different clicks
  arc end
  ```
- **Expected impact**: Human understanding of game mechanics. Informs all future experiments.

### 8. [Architecture] Try stategraph on ADCR agent framework
- **Hypothesis**: The ADCR agent has better prompt engineering and proven patterns (--- divider, multi-turn, image_diff). Combining ADCR's reasoning with stategraph's exploration might work better than either alone.
- **Files to modify**: Merge ADCR prompts with stategraph logic
- **Changes**: Use ADCR prompt patterns for LLM calls in stategraph. Call ADCR at key decision points.
- **Expected impact**: Better LLM reasoning quality when LLM is called.

---

## Completed

- **Stategraph 001**: Baseline — 120 actions in 17s, score 0.
- **Stategraph 002**: Click diagnostic — vc33 clicks work, ft09 broken.
- **Stategraph 003**: Qwen3-32B — 2x slower, same score. Reverted.
- **Stategraph 004**: No LLM — 12x faster (1.4s), same score. Reverted.
- **Stategraph 005**: BFS to frontier — better navigation, same score. Reverted.
- **Stategraph 006**: 5-tier priority + 200 actions — vc33 GAME_OVER (lives). Reverted.
- **Stategraph 007**: Click cache clear + no LLM — 600 actions in 6.6s, still 0. Reverted.
- **Stategraph 008**: 500 actions deep — 1500 in 20s. ls20: 100 unique states. vc33: GAME_OVER. Reverted.
- **Stategraph 009**: UCB1 — smarter selection doesn't help. Reverted.
- **Stategraph 010**: State-aware clicks + priority — 1000 on vc33 → GAME_OVER. Reverted.
- **Stategraph 011**: Click-effect tracking — finds right objects, can't solve sequence. Reverted.
- **Stategraph 012**: LLM-guided first click — Qwen3.5 can't identify correct targets. Reverted.
- **Stategraph 013**: LS20 LLM-guided navigation — Qwen3.5 spatial reasoning too weak. Reverted.
- **Stategraph 014**: Skip color 9 — WRONG: color mappings differ per instance. Color 1 doesn't exist. Reverted.
- **Explorer 001-030**: All reverted. See log_archive_explorer.md.
