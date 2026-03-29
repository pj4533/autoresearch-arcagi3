# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29): After 30 experiments scoring 0 with the explorer agent (LLM-per-step), pivot to the stategraph agent (programmatic exploration). Competition data is clear: training-free graph exploration beat ALL LLM approaches. The stategraph_agent already exists and has NEVER been benchmarked. Also: the click pipeline is broken — 2/3 games can't score until this is fixed.**

---

### 1. [Architecture] Benchmark stategraph_agent — zero code changes needed
- **Hypothesis**: The stategraph_agent already exists in the codebase, is fully registered, and matches the architecture of the 2nd/3rd place competition winners. It builds directed state graphs, systematically tries untried actions, and only calls the LLM every 15 steps. After 30 experiments of prompt/strategy tweaks on the explorer agent scoring 0, the programmatic approach is the obvious next step. Competition data: 3rd place graph explorer (training-free) beat ALL LLM approaches.
- **Files to modify**: None — just run with `--agent stategraph`
- **Changes**: Run `uv run python run_benchmark.py --agent stategraph --max-actions 40`. Compare speed, action diversity, and score to explorer baseline. This is the single highest-priority experiment.
- **Expected impact**: Dramatically faster (most actions skip LLM). May score on LS20 since it systematically explores all untried actions from each state. Even if score stays 0, establishes the programmatic baseline for all future experiments.

### 2. [Bug Fix] Debug click pipeline — verify clicks work end-to-end
- **Hypothesis**: Experiments 004-022 found clicks produce "no visible change." Code tracing reveals the agent coordinate pipeline IS correct: agent outputs 0-127, base agent does //2, API receives 0-63 display coordinates. The issue is likely **target selection** (clicking non-interactive cells). BUT: the arc CLI's local backend passes coordinates AS-IS to arcengine (no //2), while the agent path goes through the API with //2. These may use different coordinate conventions. Need to verify which convention each path expects.
- **Files to modify**: Diagnostic only — no code changes until root cause confirmed
- **Changes**: Two diagnostic tests:
  1. **CLI test** (local backend, coordinates sent as-is to arcengine):
  ```bash
  arc start vc33 --max-actions 40
  arc state --image
  arc action click --x 34 --y 24   # Grid coords for sprite AEF (set_position x=34,y=24)
  arc state --image                 # Did anything change?
  arc action click --x 16 --y 14   # Grid coords for sprite XTW
  arc state --image
  arc end
  ```
  Also try with doubled coords (x=68, y=48) in case arcengine expects 0-127. The key question: does `arc action click` expect grid coordinates (0-63) or display coordinates (0-127)?
  2. **Agent path test**: Run stategraph on vc33 only with verbose logging to see exact x,y values reaching the API.
- **Expected impact**: Confirms whether click pipeline works and what coordinate convention is needed. Unblocks ft09 and vc33.

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

### 6. [Exploration Strategy] BFS shortest-path-to-frontier in stategraph
- **Hypothesis**: When all actions from the current state are tried, the stategraph agent currently navigates to neighbors (Priority 4-5) or does a random walk (Priority 6). The 3rd-place winner used BFS across the entire known graph with a reverse-edge distance map. Each node stores its distance to the nearest frontier (state with untried actions). When current state is exhausted, follow the `next_hop` chain to reach the frontier optimally.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Maintain a reverse graph `_G_rev` (target → source edges) alongside the forward graph
  2. Add `_rebuild_distances()`: BFS from all frontier nodes through `_G_rev`, computing distance-to-frontier for every known state. Store `distance` and `next_hop` (the action to take) per node
  3. Rebuild distances whenever a node becomes "closed" (all actions tried)
  4. In `_choose_action()`: if current state has untried actions, pick one (randomly, like 3rd place does). If exhausted, follow `next_hop` chain — pick any action whose target has `distance == current.distance - 1`
  5. Replace Priority 4-6 entirely with this BFS navigation
- **Expected impact**: Eliminates random walks. Agent always takes the optimal path to unexplored territory. The 3rd-place solution's core algorithmic advantage.

### 7. [Exploration Strategy] 5-tier click priority groups for stategraph
- **Hypothesis**: The 3rd-place solution groups ALL connected components (not just small ones) into 5 priority tiers. Actions within each tier are exhausted across the ENTIRE graph before moving to the next tier. This ensures interactive buttons are found before clicking background noise.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`, `src/arcagi3/utils/formatting.py`
- **Changes**: Based on exact 3rd-place implementation:
  - **Group 0 (highest)**: Salient color (6-15) AND medium size (2-32px per dimension). Also: ALL movement/arrow actions go in group 0.
  - **Group 1**: Non-salient color (0-5) AND medium size
  - **Group 2**: Salient color AND wrong size (too small or too large)
  - **Group 3**: Not salient, not medium, not status bar
  - **Group 4 (lowest)**: Status bar segments
  - Each connected component = one click target. Click a random pixel within the segment (ensures clicking ON objects, not in empty space).
  - Process groups sequentially: exhaust ALL group 0 actions across ALL states before any group 1.
- **Expected impact**: Finds interactive objects in ~5-10 clicks instead of 50+. The 3rd-place solution's targeting advantage.

### 8. [Preprocessing] Rule-based status bar detection for stategraph
- **Hypothesis**: Our stategraph masks a fixed 2 rows top/bottom as status bar. The 3rd-place solution detects status bars dynamically using connected component analysis: segments touching screen edges with elongated aspect ratio (>5:1) OR having 3+ "twin" segments (same color/area/shape) along an edge. Fixed masking misses sidebar counters, dot indicators, and varying-height UI elements — causing the state graph to explode with false-unique states.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add `_detect_status_bar()` method, run once per level (on level_up):
  1. Find all connected components via flood fill
  2. Mark as status bar if: touches any screen edge (within 3px) AND (aspect ratio > 5:1 OR has 3+ twins along the same edge)
  3. Create a boolean mask of status bar pixels
  4. Apply mask before hashing: `grid[mask] = sentinel_value`
  5. Re-run detection on each level transition (status bar layout may change)
- **Expected impact**: Prevents state space explosion from changing counters/timers. More reliable state hashing = better graph exploration.

### 9. [State Tracking] Suspicious transition handling
- **Hypothesis**: Some actions trigger animations or temporary visual changes that revert. The 3rd-place solution marks transitions as "suspicious" when they lead back to the initial frame of the current level. It requires 3 confirmations before recording a suspicious transition as real. This handles non-determinism, animations, and game resets gracefully.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track `level_initial_hash` (first frame hash after score increase). When a transition's target equals `level_initial_hash` and multiple frames were returned, mark it suspicious. Only record after 3 occurrences. This prevents the graph from being poisoned by transient states.
- **Expected impact**: Cleaner state graphs, fewer false transitions, more reliable exploration.

### 10. [Exploration Strategy] UCB1 action selection for stategraph
- **Hypothesis**: Instead of trying untried actions in arbitrary order, use UCB1 (Upper Confidence Bound): `score = exploitation_value + C * sqrt(ln(total_visits) / action_visits)`. Actions that produce state changes get higher exploitation values. Rarely-tried actions get exploration bonus. This is the core of MCTS and can be implemented in a few lines.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track per-action visit counts and reward (frame_changed = 1, no_change = 0, score_increase = 10). In `_choose_action()`, compute UCB1 score for each action and pick the highest. Still try untried actions first (infinite exploration bonus).
- **Expected impact**: Smarter action selection. Exploits actions known to produce changes while still exploring untried ones.

### 11. [Architecture] Code-generation approach (Symbolica-style)
- **Hypothesis**: Symbolica scored 36.08% on ARC-AGI-3 by having LLM agents write Python code to interact with games, not by choosing individual actions. One cloud API call generates a strategy function, then the function runs for 100+ actions at zero cost. This is fundamentally different from our LLM-per-step or programmatic-per-step approach.
- **Files to modify**: New agent or modification to stategraph
- **Changes**: At step 0, call Claude Sonnet with grid description and game mechanics. Ask it to write a Python function: `def choose_action(grid, available_actions, history) -> action`. Execute this function for all subsequent steps. Re-generate if score stalls. Cost: ~$0.05 per game.
- **Expected impact**: Leverages cloud model intelligence for strategy design while keeping execution cost near zero.

### 12. [Exploration Strategy] LS20 object detection + pathfinding
- **Hypothesis**: LS20 has known mechanics: keys, doors, rotators, health replenishers. The agent can detect these as connected components with distinct colors/shapes. A* or BFS pathfinding from player position to target objects would be far more effective than random exploration. The sequence: find player → find nearest key/door → navigate there.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py` or new LS20-specific logic
- **Changes**: Add object detection: identify player (unique color/size), keys, doors, rotators by their visual signatures. Implement A* pathfinding on the grid. Plan path to nearest target and execute as movement sequence.
- **Expected impact**: Direct navigation instead of random exploration. LS20 level 1 needs 29 moves — efficient pathfinding could solve it in under 87 actions (score threshold).

### 13. [Preprocessing] Auto-detect game type from available actions
- **Hypothesis**: The 3 games have radically different mechanics. Auto-detecting game type from available_actions (movement-only vs click-only vs hybrid) and routing to specialized strategies would improve exploration immediately.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: At init: check `available_actions`. If only ACTION6 → click-only game (vc33), use click-focused strategy. If ACTION1-5 only → movement game (ls20), use graph exploration. If mixed → hybrid (ft09). Adjust click queue size, LLM interval, and priority ordering per game type.
- **Expected impact**: No more wasting movement actions in click-only games or vice versa.

### 14. [Action Sequencing] Winning sequence replay with variations
- **Hypothesis**: The stategraph agent already replays winning sequences on new levels. But game levels vary, so exact replay rarely works. Adding small variations (±1 position on clicks, ±1 step on movements) around winning sequences could discover the right adaptation faster.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After replaying a winning sequence fails (no score increase), try variations: offset click positions by ±1 grid cell, add/remove single actions from the sequence. Track which variations produce progress.
- **Expected impact**: Faster level completion after first level is solved.

### 15. [State Tracking] Curiosity-driven action prioritization
- **Hypothesis**: Track a simple prediction model: "from state S, action A leads to state S'." When the actual result differs from prediction, that's a "surprise" — prioritize actions with high surprise rate. This implements intrinsic curiosity without neural networks.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Maintain transition table. For each (state, action) pair, record expected next state. Compute surprise = 1 if actual != expected, 0 otherwise. Weight action selection toward high-surprise actions in `_choose_action()`.
- **Expected impact**: Focuses exploration on the most informative actions — the ones that reveal new game mechanics.

### 16. [Memory Management] Cross-level action knowledge transfer
- **Hypothesis**: Currently the stategraph agent clears the state graph on level transition but preserves action_knowledge. We should also preserve: which action TYPES produced state changes, which click regions were interactive, and the general game mechanic model. This bootstraps new levels.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: On level transition, preserve: `action_knowledge`, `click_results` (which regions had interactive objects), winning action types. On new level, prioritize known-productive action types first.
- **Expected impact**: Faster exploration on levels 2+ since the agent already knows the game's basic mechanics.

### 17. [Phase Transitions] Exhaustive-then-exploit transition in stategraph
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
