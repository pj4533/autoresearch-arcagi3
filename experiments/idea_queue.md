# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29): After 30 experiments scoring 0 with the explorer agent (LLM-per-step), pivot to the stategraph agent (programmatic exploration). Competition data is clear: training-free graph exploration beat ALL LLM approaches. The stategraph_agent already exists and has NEVER been benchmarked. Also: the click pipeline is broken — 2/3 games can't score until this is fixed.**

---

### 1. [Architecture] Benchmark stategraph_agent — zero code changes needed
- **Hypothesis**: The stategraph_agent already exists in the codebase, is fully registered, and matches the architecture of the 2nd/3rd place competition winners. It builds directed state graphs, systematically tries untried actions, and only calls the LLM every 15 steps. After 30 experiments of prompt/strategy tweaks on the explorer agent scoring 0, the programmatic approach is the obvious next step. Competition data: 3rd place graph explorer (training-free) beat ALL LLM approaches.
- **Files to modify**: None — just run with `--agent stategraph`
- **Changes**: Run `uv run python run_benchmark.py --agent stategraph --max-actions 40`. Compare speed, action diversity, and score to explorer baseline. This is the single highest-priority experiment.
- **Expected impact**: Dramatically faster (most actions skip LLM). May score on LS20 since it systematically explores all untried actions from each state. Even if score stays 0, establishes the programmatic baseline for all future experiments.

### 2. [Bug Fix] Debug click pipeline — why do clicks produce no frame changes?
- **Hypothesis**: Experiments 004, 007, 013, 021, 022 all found that ACTION6 (click) produces "no visible change" in ft09 and vc33, even after the frame comparison fix. This blocks 2/3 games entirely. The root cause is unknown — it could be coordinate mapping, camera transforms, or a local server issue.
- **Files to modify**: Diagnostic only — no code changes until root cause is found
- **Changes**: Run manual test with arc CLI:
  ```bash
  arc start vc33 --max-actions 40
  arc state --image
  arc action click --x 68 --y 48   # Known clickable sprite AEF
  arc state --image                 # Did anything change?
  arc action click --x 32 --y 28   # Known clickable sprite XTW
  arc state --image
  arc end
  ```
  If manual clicks work but agent clicks don't → bug in action data format. If manual clicks also fail → local server click handling bug. Known clickable sprite positions from VC33 source: AEF(68,48), XTW(32,28), mZh(114,92), WGb(84,50), dkk(0,24).
- **Expected impact**: Unblocks ft09 and vc33 scoring entirely. VC33 level 1 needs only 6 clicks — easiest path to first non-zero score.

### 3. [Architecture] Try Qwen3-32B dense model
- **Hypothesis**: Qwen3.5-35B-A3B is a MoE model activating only 3B parameters per forward pass. Qwen3-32B is dense (all 32B params active) with standard attention (KV cache works). It may have fundamentally better reasoning quality. With KV cache reuse, repeated prompts are faster despite slower raw generation (20-30 vs 60-70 tok/s).
- **Files to modify**: None — just run with `--config qwen3-32b-local`
- **Changes**: Run `uv run python run_benchmark.py --agent stategraph --config qwen3-32b-local --max-actions 40`. Compare score and hypothesis quality to qwen3.5-35b. Also try explorer agent with qwen3-32b for comparison.
- **Expected impact**: If bottleneck is model reasoning (likely after 30 prompt experiments failed), a better model solves it directly.

### 4. [Architecture] Cloud model validation — is the framework broken?
- **Hypothesis**: After 30 experiments scoring 0 with Qwen3.5-35B, we don't know if the problem is the model or the framework. Running with Claude Sonnet (a proven strong model) answers this definitively. If Claude scores > 0, the model is the bottleneck and we should focus on model selection/programmatic approaches. If Claude also scores 0, there's a framework bug.
- **Files to modify**: None — just run with a cloud config
- **Changes**: Run `uv run python run_benchmark.py --agent explorer --config claude-sonnet-4-5-20250929-thinking-8k --max-actions 40 --games ls20`. Single game to minimize cost. Compare score to Qwen baseline.
- **Expected impact**: Either confirms model capability is the bottleneck (focus on stategraph/programmatic) or reveals framework bugs.

### 5. [Exploration Strategy] Remove LLM calls entirely from stategraph
- **Hypothesis**: The 3rd-place competition winner used ZERO LLM calls and still beat all LLM approaches. Our stategraph agent calls the LLM every 15 steps for hypothesis formation. This wastes 15-30 seconds per LLM call and the hypotheses can't improve action selection when the model isn't strong enough. Pure programmatic exploration is faster and more systematic.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Set `LLM_INTERVAL = 0` or add a flag to skip LLM calls entirely. All actions chosen purely by graph exploration logic. This maximizes actions per time budget and tests whether programmatic exploration alone can score.
- **Expected impact**: ~15x more actions in same time budget. Systematic coverage of entire state space.

### 6. [Exploration Strategy] Shortest-path-to-frontier via BFS in stategraph
- **Hypothesis**: When all actions from the current state are tried, the stategraph agent currently navigates to neighbors (Priority 4-5) or does a random walk (Priority 6). The 3rd-place winner instead BFS-navigated to the nearest state with untried actions across the entire known graph. This is much more efficient — instead of random walking, it replays a known path to reach unexplored territory.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add `_bfs_to_frontier()` method: BFS from current state through known transitions to find nearest state with untried actions. Return the path. Execute path actions in sequence. Replace Priority 4-6 in `_choose_action()` with this BFS navigation.
- **Expected impact**: Eliminates random walks entirely. Agent always takes the shortest path to new territory. Critical for LS20 where the state space is large.

### 7. [Exploration Strategy] 5-tier click priority system for stategraph
- **Hypothesis**: The 3rd-place solution used 5 priority tiers for click targets based on connected component analysis: (1) small button-like objects, (2) colorful distinct objects, (3) medium structural elements, (4) large areas, (5) background. Current stategraph clicks detected objects in size order without prioritization.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`, `src/arcagi3/utils/formatting.py`
- **Changes**: In `_try_click()`, rank detected objects by: (a) size < 50 cells (button-like), (b) color distinctness from background, (c) aspect ratio near 1:1 (square = button), (d) distance from borders. Click high-priority targets first. Skip structural colors (0=white, 5=black, 4=gray).
- **Expected impact**: Finds interactive objects faster. Critical for vc33 and ft09 where only specific sprites are clickable.

### 8. [Exploration Strategy] UCB1 action selection for stategraph
- **Hypothesis**: Instead of trying untried actions in arbitrary order, use UCB1 (Upper Confidence Bound): `score = exploitation_value + C * sqrt(ln(total_visits) / action_visits)`. Actions that produce state changes get higher exploitation values. Rarely-tried actions get exploration bonus. This is the core of MCTS and can be implemented in a few lines.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track per-action visit counts and reward (frame_changed = 1, no_change = 0, score_increase = 10). In `_choose_action()`, compute UCB1 score for each action and pick the highest. Still try untried actions first (infinite exploration bonus).
- **Expected impact**: Smarter action selection. Exploits actions known to produce changes while still exploring untried ones.

### 9. [Architecture] Code-generation approach (Symbolica-style)
- **Hypothesis**: Symbolica scored 36.08% on ARC-AGI-3 by having LLM agents write Python code to interact with games, not by choosing individual actions. One cloud API call generates a strategy function, then the function runs for 100+ actions at zero cost. This is fundamentally different from our LLM-per-step or programmatic-per-step approach.
- **Files to modify**: New agent or modification to stategraph
- **Changes**: At step 0, call Claude Sonnet with grid description and game mechanics. Ask it to write a Python function: `def choose_action(grid, available_actions, history) -> action`. Execute this function for all subsequent steps. Re-generate if score stalls. Cost: ~$0.05 per game.
- **Expected impact**: Leverages cloud model intelligence for strategy design while keeping execution cost near zero.

### 10. [Exploration Strategy] LS20 object detection + pathfinding
- **Hypothesis**: LS20 has known mechanics: keys, doors, rotators, health replenishers. The agent can detect these as connected components with distinct colors/shapes. A* or BFS pathfinding from player position to target objects would be far more effective than random exploration. The sequence: find player → find nearest key/door → navigate there.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py` or new LS20-specific logic
- **Changes**: Add object detection: identify player (unique color/size), keys, doors, rotators by their visual signatures. Implement A* pathfinding on the grid. Plan path to nearest target and execute as movement sequence.
- **Expected impact**: Direct navigation instead of random exploration. LS20 level 1 needs 29 moves — efficient pathfinding could solve it in under 87 actions (score threshold).

### 11. [Preprocessing] Auto-detect game type from available actions
- **Hypothesis**: The 3 games have radically different mechanics. Auto-detecting game type from available_actions (movement-only vs click-only vs hybrid) and routing to specialized strategies would improve exploration immediately.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: At init: check `available_actions`. If only ACTION6 → click-only game (vc33), use click-focused strategy. If ACTION1-5 only → movement game (ls20), use graph exploration. If mixed → hybrid (ft09). Adjust click queue size, LLM interval, and priority ordering per game type.
- **Expected impact**: No more wasting movement actions in click-only games or vice versa.

### 12. [Action Sequencing] Winning sequence replay with variations
- **Hypothesis**: The stategraph agent already replays winning sequences on new levels. But game levels vary, so exact replay rarely works. Adding small variations (±1 position on clicks, ±1 step on movements) around winning sequences could discover the right adaptation faster.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After replaying a winning sequence fails (no score increase), try variations: offset click positions by ±1 grid cell, add/remove single actions from the sequence. Track which variations produce progress.
- **Expected impact**: Faster level completion after first level is solved.

### 13. [State Tracking] Curiosity-driven action prioritization
- **Hypothesis**: Track a simple prediction model: "from state S, action A leads to state S'." When the actual result differs from prediction, that's a "surprise" — prioritize actions with high surprise rate. This implements intrinsic curiosity without neural networks.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Maintain transition table. For each (state, action) pair, record expected next state. Compute surprise = 1 if actual != expected, 0 otherwise. Weight action selection toward high-surprise actions in `_choose_action()`.
- **Expected impact**: Focuses exploration on the most informative actions — the ones that reveal new game mechanics.

### 14. [Memory Management] Cross-level action knowledge transfer
- **Hypothesis**: Currently the stategraph agent clears the state graph on level transition but preserves action_knowledge. We should also preserve: which action TYPES produced state changes, which click regions were interactive, and the general game mechanic model. This bootstraps new levels.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: On level transition, preserve: `action_knowledge`, `click_results` (which regions had interactive objects), winning action types. On new level, prioritize known-productive action types first.
- **Expected impact**: Faster exploration on levels 2+ since the agent already knows the game's basic mechanics.

### 15. [Phase Transitions] Exhaustive-then-exploit transition in stategraph
- **Hypothesis**: Once the state graph shows that all reachable states have been fully explored (no untried actions anywhere), the agent should switch from exploration to exploitation: replay the sequence that produced the most state changes or the highest score. Currently it random-walks when stuck.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track total untried actions across all known states. When this hits 0, switch to exploitation mode: replay the longest path that produced unique state transitions, or try action sequences that haven't been tried as combinations.
- **Expected impact**: Prevents wasted actions on fully-explored state spaces. Focuses remaining budget on execution.

---

## Completed

- **#1 [Prompt Engineering] Game-type-aware system prompt** — Exp 002: reverted (score=0.0000). Model tried correct actions but JSON output still malformed.
- **#2 [Exploration Strategy] Fix three hardcoded Move Up fallbacks** — Exp 003: reverted (score=0.0000). ls20 regressed to 0 actions. Root cause is JSON parse failure, not fallback logic.
- **#3 [Exploration Strategy] Programmatic click probe** — Exp 004: reverted (score=0.0000). 2x faster but all clicks "no visible change" — coordinate mapping wrong.
- **#4 [Prompt Engineering] Eliminate convert LLM call** — Exp 005: reverted (score=0.0000). Model sometimes produces JSON but truncated by max_tokens.
- **#27 [Prompt Engineering] Disable Qwen thinking mode** — Exp 006: ACCEPTED (foundational fix). JSON parse 0%→91%, duration 41% faster. Unblocks all other ideas.
- **#5 [Preprocessing] Click target list in explore prompt** — Exp 007: reverted (score=0.0000). Click targets shown but clicks still don't register visible changes.
- **#6 [State Tracking] State graph with loop detection** — Exp 008: reverted (score=0.0000). Fastest run (2491s) but no score improvement.
- **#7 [State Tracking] Enhanced frame change description** — Exp 009: reverted (score=0.0000). New speed record (1949s) but still no score.
- **#8 [Prompt Engineering] StateAct-style structured prompting** — Exp 010: reverted (score=0.0000). Best JSON parse rate (1 failure) but no score.
- **#9 [Phase Transitions] Stuck detection + random fallback** — Exp 011: reverted (score=0.0000). Very fast (1003s) but random actions don't score.
- **#10 [Memory Management] Structured memory** — Exp 012: reverted (score=0.0000). No improvement.
- **#32 [Exploration Strategy] Brute-force click for VC33** — Exp 013: reverted (score=0.0000). Corrected coords still no visible change. Click issue is NOT coordinate mapping.
- **#11 [Action Sequencing] Multi-action planning** — Exp 014: reverted (score=0.0000). 85% faster but no score.
- **#13 [Prompt Engineering] ReflAct-style reflection** — Exp 015: reverted (score=0.0000). No improvement.
- **#16 [Prompt Engineering] Score change feedback** — Exp 016: reverted (score=0.0000). No score changes ever occur so feedback never triggers.
- **#20 [Memory Management] Multi-turn conversation context** — Exp 017: reverted (score=0.0000). Slower due to extra tokens.
- **#1(new) [Exploration Strategy] Hypothesis-driven exploration** — Exp 018: reverted (score=0.0000). Hypotheses formed but no score.
- **#2(new) [Memory Management] Action-effect journal** — Exp 019: reverted (score=0.0000). Journal tracks but model can't discover scoring mechanics.
- **#3(new) [State Tracking] State graph with untried actions** — Exp 020: reverted (score=0.0000). Fast but no score.
- **#6(new) [Exploration Strategy] Systematic probe with clicks** — Exp 021: reverted (score=0.0000). DIAGNOSTIC: found frame comparison timing bug.
- **fix [Bug Fix] Frame comparison timing** — Exp 022: ACCEPTED. Agent can now see action effects.
- **#5(new) [State Tracking] Enhanced frame descriptions** — Exp 023: reverted (score=0.0000). Rich descriptions working but no score.
- **#8(new) [Prompt Engineering] Eliminate convert LLM call** — Exp 024: reverted (score=0.0000). Faster but no score.
- **#10(new) [Exploration Strategy] Probe undo** — Exp 025: reverted (score=0.0000). Undo not available in these games.
- **#14(new) [Preprocessing] Grid differencing** — Exp 026: reverted (score=0.0000). Detailed diffs working but no score.
- **#15(new) [Prompt Engineering] Prompt compression** — Exp 027: reverted (score=0.0000). Fastest ls20 (373s) but no score.
- **#12(new) [Action Sequencing] Multi-action planning** — Exp 028: reverted (score=0.0000). Fastest benchmark (1390s) but no score.
- **#15(new) [Architecture] ALL best changes combined** — Exp 029: reverted (score=0.0000). Compound effect still 0. Model lacks reasoning for these games.
- **#16(new) [Architecture] max_actions=100** — Exp 030: reverted (score=0.0000). 300 actions, still 0. Budget isn't the bottleneck.
- **#4 [Memory Management] Cross-level knowledge transfer** — Exp 031: reverted (score=0.0000). No level transitions occur so transfer never activates.
- **#1 [Architecture] Stategraph baseline** — Exp 032: baseline (score=0.0000). 120 actions in 17s. LLM detects grid changes but can't score. Establishes programmatic baseline.
