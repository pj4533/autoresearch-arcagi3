# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 017): 47 experiments, ALL score 0. Programmatic exploration is blocked (life mechanics). Qwen3.5-35B can't reason. No cloud API keys. The #1 ACTIONABLE experiment is QwQ-32B — a DIFFERENT reasoning model (NOT Qwen3-32B which was exp 003). QwQ is trained for chain-of-thought reasoning with 8192 max tokens.**

**NOTE TO EXECUTOR: Skip #1 (needs API key). Start with #2 (QwQ-32B) — it's a local model, no API key needed. Just change `--config qwq-32b-local`. This is the MOST IMPORTANT experiment to run next.**

---

### 1. [Architecture] Cloud model validation — NEEDS ANTHROPIC_API_KEY
- **Hypothesis**: 45 experiments scoring 0 with local models. We don't know if the framework works. Claude Sonnet 4.5 would answer this definitively.
- **Files to modify**: `.env` (add ANTHROPIC_API_KEY), then CLI args only
- **Changes**:
  1. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...` (user needs to provide this)
  2. Run: `uv run python run_benchmark.py --agent explorer --config claude-sonnet-4-5-20250929-thinking-8k --max-actions 40 --games vc33-9851e02b`
  3. Cost: ~$0.50-2.00 for a single game
- **Expected impact**: Determines if framework works. If Claude scores > 0, model intelligence is the bottleneck. If also 0, framework bug.
- **SKIP IF**: No API key available. Move to #2.

### 2. [Architecture] QwQ-32B reasoning model — chain-of-thought for puzzles
- **Hypothesis**: QwQ-32B is specifically designed for reasoning tasks with explicit chain-of-thought. Unlike Qwen3.5-35B (MoE, 3B active params) or Qwen3-32B (dense, tested in exp 003), QwQ-32B is trained for step-by-step reasoning with 8192 max completion tokens (2x others). It may reason through puzzle mechanics that Qwen3.5 can't. At 20-30 tok/s it's slower but each response should be higher quality reasoning.
- **Files to modify**: None — CLI args only
- **Changes**: Run `uv run python run_benchmark.py --agent explorer --config qwq-32b-local --max-actions 40 --games vc33-9851e02b`. Single game to test reasoning quality. Also try ls20: `--games ls20-cb3b57cc`.
- **Expected impact**: QwQ's chain-of-thought reasoning may identify game mechanics that Qwen3.5 misses. Best available local reasoning model.

### 3. [Architecture] Manual game play — human understands mechanics
- **Hypothesis**: After 45 automated experiments, nobody has manually played these games. A human playing vc33 for 5 minutes would reveal: what do clicks do? what's the goal? what does a winning sequence look like? This insight is worth more than 10 automated experiments.
- **Files to modify**: None — manual exploration
- **Changes**:
  ```bash
  # Make sure local server is running first
  uv run python start_local_server.py &

  arc start vc33 --max-actions 50
  arc state --image    # Look at the grid
  # Try clicking different objects
  arc action click --x 60 --y 24    # One of the detected interactive objects
  arc state --image    # What changed?
  # Keep experimenting...
  arc end
  ```
  Then do the same for ls20:
  ```bash
  arc start ls20 --max-actions 50
  arc state --image
  arc action move_right
  arc state --image
  # Navigate and observe...
  arc end
  ```
- **Expected impact**: Human understanding of actual game mechanics → targeted strategy.

### 4. [Architecture] QwQ-32B + stategraph hybrid — reasoning at key moments
- **Hypothesis**: QwQ-32B is too slow for per-step calls but may excel at key decision points. Use programmatic exploration (0.012s/action) for bulk, call QwQ-32B when: (a) game starts (analyze grid), (b) after first interactive click (analyze what changed), (c) when stuck. QwQ's chain-of-thought may identify puzzle patterns.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Set `--config qwq-32b-local`. Use stategraph with LLM_INTERVAL=15 (or custom intervals at key moments). QwQ analyzes accumulated exploration data and suggests strategy.
- **Expected impact**: Combines fast exploration with quality reasoning.

### 5. [Exploration Strategy] VC33 click repetition — same object N times
- **Hypothesis**: VC33 is "volume/height adjustment." Clicking the same object multiple times may adjust its height/volume to the target value. The stategraph marks each click as "tried" and never repeats. But puzzle solution may require clicking object A three times, then object B twice.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: For click-only games: allow clicking the same object up to 10 times. Track cumulative clicks per object and effects. Stop clicking an object when effect plateaus (no more frame changes).
- **Expected impact**: If vc33 requires N clicks on same target, this is essential.

### 6. [Exploration Strategy] VC33 systematic 2-3 click combos
- **Hypothesis**: If vc33 level 1 needs 6 clicks and there are ~5-10 interactive objects, try all 2-3 click combinations systematically. C(10,2)=45, C(10,3)=120. With 50 lives, can try ~15-25 combos.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Enumerate pairs/triples of interactive objects. Click each combo, check for score. Systematic search of short sequences.
- **Expected impact**: Exhaustive search of short click sequences.

### 7. [Exploration Strategy] VC33 sequential feedback — click, observe, adapt
- **Hypothesis**: Click one interactive object, observe what changed (count cells, direction of change). Use the change pattern to decide next click. This is sequential decision-making with feedback, not batch exploration.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After each click that produces a change: analyze the delta (which cells changed, in which direction). If change moves cells toward a "goal area" (identified by pattern), repeat. If not, try different target.
- **Expected impact**: Feedback-driven sequential strategy.

### 8. [Architecture] ADCR agent with improved prompts — different reasoning approach
- **Hypothesis**: ADCR agent has proven prompt patterns (--- divider, multi-turn, image_diff) that explorer lacks. Haven't tested ADCR since infrastructure fixes. With the frame comparison fix and thinking mode fix, ADCR may perform differently.
- **Files to modify**: None — just run with different agent
- **Changes**: `uv run python run_benchmark.py --agent adcr --config qwq-32b-local --max-actions 40 --games vc33-9851e02b`
- **Expected impact**: Different prompt architecture + reasoning model = different results.

---

## Completed

- **Stategraph 001-017**: All score 0. See log above. Key findings: vc33 clicks work, ft09 broken, both games have life mechanics, Qwen3.5 can't reason about grids, programmatic exploration ceiling reached, color analysis from game code doesn't generalize to instances, click repetition doesn't work (not a slider puzzle), sequential adaptation insufficient without reasoning.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
- **NOT YET TESTED**: QwQ-32B reasoning model, cloud models (no API key), manual game play, ADCR agent with new infrastructure.
