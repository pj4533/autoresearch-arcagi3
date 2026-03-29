# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 004): Pure programmatic stategraph: 120 actions in 1.4s. vc33 clicks confirmed working (265 cell changes on color 9 blocks). ft09 game version BROKEN (only status bar changes). Focus entirely on vc33 (6 clicks to solve level 1) and ls20 (movement works). Key need: better click targeting for vc33, BFS navigation for ls20.**

---

### 1. [Exploration Strategy] VC33-focused: 5-tier click priority + more actions
- **Hypothesis**: VC33 is confirmed working (exp 002 diagnostic: color 9 blocks produce 265 cell changes). Level 1 needs only 6 clicks. The agent already detects interactive objects but doesn't prioritize well — it clicks structural elements and background. The 3rd-place solution's priority system finds interactive buttons in ~5-10 clicks. Combined with more actions (agent does 40 in 0.5s with no LLM), this is the clearest path to first score.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`, `src/arcagi3/utils/formatting.py`
- **Changes**: Two changes combined for maximum impact:
  1. **5-tier click priority**: Group connected components by color saliency + size:
     - **Group 0**: Salient color ({6-15}) AND medium size (2-32px per dim). VC33's interactive sprites are color 9 (blue) and 11 (yellow) — salient, medium → group 0.
     - **Group 1**: Non-salient ({0-5}) AND medium size
     - **Group 2**: Salient AND wrong size
     - **Group 3**: Other non-status-bar
     - **Group 4**: Status bar
     - Click random pixel within each segment (not center — ensures hitting the object).
     - Exhaust all group 0 actions across all states before trying group 1.
  2. **Increase max_actions to 200**: At 0.012s/action (no LLM), 200 actions = 2.4s. VC33 level 1 needs 6 clicks out of maybe 20-30 group-0 targets. With 200 actions, the agent can exhaustively try every group-0 click across every reachable state.

  Run: `uv run python run_benchmark.py --agent stategraph --max-actions 200 --games vc33`
- **Expected impact**: First non-zero score on vc33. With priority targeting and enough budget, the agent should click all interactive objects within ~50 actions.

### 2. [Exploration Strategy] VC33 click-only mode — skip all movement
- **Hypothesis**: VC33 ONLY supports ACTION6 (click). The stategraph currently wastes 4-5 actions per state trying movement (untried non-click Priority 2). For click-only games, movement should be eliminated entirely. This doubles the effective click budget.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_choose_action()`, check `available_actions`. If only ACTION6 is available, skip Priority 2 (untried non-click) entirely. All actions are clicks at detected objects. Also: after learning that movement doesn't work (from action_knowledge showing all movement = "no visible change"), permanently skip movement actions for the rest of the game.
- **Expected impact**: Doubles effective click budget for vc33. Every action is a meaningful click.

### 3. [Exploration Strategy] 5-tier click priority groups for stategraph (general)
- **Hypothesis**: Exp 032 shows vc33 "detects click effects but no score" — the agent clicks objects and sees changes but doesn't solve levels. The issue is targeting: current `detect_interactive_objects()` filters to size < 200 which catches structural elements. The 3rd-place solution's 5-tier priority system based on color saliency + size finds interactive buttons in ~5-10 clicks.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`, `src/arcagi3/utils/formatting.py`
- **Changes**: Based on 3rd-place implementation:
  - **Group 0 (highest)**: Salient color ({6,7,8,9,10,11,12,13,14,15}) AND medium size (2-32px per dimension). Also: ALL movement/arrow actions.
  - **Group 1**: Non-salient color ({0,1,2,3,4,5}) AND medium size
  - **Group 2**: Salient color AND wrong size (too small or too large)
  - **Group 3**: Not salient, not medium, not status bar
  - **Group 4 (lowest)**: Status bar segments
  - Each connected component = one click target. Click a random pixel within the segment.
  - Process groups sequentially: exhaust all group 0 actions across all states before any group 1.
- **Expected impact**: Targets interactive buttons first. vc33's interactive sprites have salient colors (9=blue, 11=yellow) and medium sizes — they'd be group 0.

### 4. [Exploration Strategy] BFS shortest-path-to-frontier in stategraph
- **Hypothesis**: When all actions from the current state are tried, the stategraph does a random walk (Priority 6). The 3rd-place winner used BFS across the entire graph: compute distance from every node to the nearest "frontier" (state with untried actions), then follow the shortest path.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Maintain a reverse graph `_G_rev` (target → source edges)
  2. Add `_rebuild_distances()`: BFS from all frontier nodes through `_G_rev`, stores `distance` and `next_hop` per node
  3. Rebuild on node closure (all actions tried)
  4. In `_choose_action()`: if exhausted, follow `next_hop` chain instead of random walk
  5. Replace Priority 4-6 entirely
- **Expected impact**: Eliminates random walks. Agent always takes shortest path to unexplored territory.

### 5. [Exploration Strategy] Increase max_actions for stategraph
- **Hypothesis**: Exp 032 ran 120 actions in 17s (0.14s/action). The stategraph is so fast we can afford 200-500 actions within a few minutes. With pure programmatic (no LLM), even 1000 actions takes ~2 minutes. More actions = more thorough state space coverage.
- **Files to modify**: None — just change `--max-actions`
- **Changes**: Run `uv run python run_benchmark.py --agent stategraph --max-actions 200`. At 0.14s/action, 200 actions = 28s.
- **Expected impact**: More thorough exploration. LS20 level 1 needs 29 baseline moves; with 200 budget the agent can afford extensive exploration.

### 6. [Preprocessing] Rule-based status bar detection for stategraph
- **Hypothesis**: Our stategraph masks fixed 2 rows top/bottom. The 3rd-place solution detects status bars dynamically via connected component analysis: segments touching edges with elongated aspect ratio (>5:1) OR 3+ "twin" segments along an edge.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Add `_detect_status_bar()`, run once per level:
  1. Find all connected components via flood fill
  2. Mark as status bar if: touches screen edge (within 3px) AND (aspect ratio > 5:1 OR 3+ twins on same edge)
  3. Create boolean mask, apply before hashing
- **Expected impact**: Prevents state space explosion from changing counters/timers.

### 7. [State Tracking] Suspicious transition handling
- **Hypothesis**: Some actions trigger animations that revert. 3rd-place requires 3 confirmations before recording a transition back to the level's initial frame.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track `level_initial_hash`. When transition target equals it AND multiple frames returned, require 3 occurrences before recording.
- **Expected impact**: Cleaner graphs, fewer false transitions.

### 8. [Architecture] Try Qwen3-32B dense model with stategraph
- **Hypothesis**: The stategraph only calls LLM every 15 steps, so model speed matters less. Qwen3-32B dense (all 32B params active, KV cache) may produce better hypotheses.
- **Files to modify**: None — just `--config qwen3-32b-local`
- **Changes**: Run `uv run python run_benchmark.py --agent stategraph --config qwen3-32b-local --max-actions 40`.
- **Expected impact**: Better LLM reasoning when called.

### 9. [Architecture] Cloud model validation (Claude Sonnet)
- **Hypothesis**: Run Claude Sonnet to determine if any agent can score. If Claude + explorer scores > 0, the model is the bottleneck.
- **Files to modify**: None — CLI args only
- **Changes**: `uv run python run_benchmark.py --agent explorer --config claude-sonnet-4-5-20250929-thinking-8k --max-actions 40 --games ls20`. Single game, minimize cost.
- **Expected impact**: Separates model capability from framework issues.

### 10. [Architecture] Code-generation approach (Symbolica-style)
- **Hypothesis**: Symbolica scored 36.08% by having LLM write Python code to play games. One API call generates strategy, runs for 100+ actions free.
- **Files to modify**: New agent or stategraph modification
- **Changes**: At step 0, call Claude Sonnet with grid + mechanics. Generate `def choose_action(grid, history) -> action`. Execute for all steps.
- **Expected impact**: Cloud model intelligence for strategy, zero per-action cost.

### 11. [Exploration Strategy] LS20 object detection + pathfinding
- **Hypothesis**: LS20 has keys, doors, rotators, health. Detect via connected components, implement A* pathfinding to targets.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Identify player, keys, doors by color/size. A* to nearest target. Execute as movement sequence.
- **Expected impact**: Direct navigation vs random exploration.

### 12. [Exploration Strategy] UCB1 action selection
- **Hypothesis**: Use UCB1 to balance exploit (frame-changing actions) with explore (untried). `score = reward + C * sqrt(ln(N) / n_i)`.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track per-action rewards. frame_changed=1, score_increase=10. Pick highest UCB1.
- **Expected impact**: Smarter exploration/exploitation balance.

### 13. [Action Sequencing] Winning sequence replay with variations
- **Hypothesis**: After solving a level, try same sequence on next level with ±1 variations.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Offset clicks ±1 cell, add/remove single actions from winning sequences.
- **Expected impact**: Faster level 2+ completion.

### 14. [State Tracking] Curiosity-driven action prioritization
- **Hypothesis**: Prioritize actions whose outcomes are most surprising (actual != predicted). Simple lookup table.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track transition predictions. Weight selection toward high-surprise actions.
- **Expected impact**: Focuses on most informative actions.

### 15. [Memory Management] Cross-level action knowledge transfer
- **Hypothesis**: Preserve which action TYPES worked and which click regions were interactive across levels.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Preserve click_results and action effectiveness on level transition.
- **Expected impact**: Faster exploration on levels 2+.

### 16. [Phase Transitions] Exhaustive-then-exploit transition
- **Hypothesis**: When state graph has zero untried actions anywhere, switch to exploitation mode.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track total untried actions. When 0, replay best sequence or try combinations.
- **Expected impact**: Prevents wasted actions on exhausted state spaces.

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
- **#4(old) [Memory Management] Cross-level knowledge transfer** — Exp 031: reverted (score=0.0000). No level transitions occur so feature never activates.
- **#1(queue) [Architecture] Stategraph baseline** — Exp 032: baseline (score=0.0000). 120 actions in 17s (0.14s/act). Clicks work in vc33. ft09 wastes actions on movement. Establishes programmatic baseline.
- **#2(queue) [Bug Fix] Click diagnostic** — Exp 033: vc33 clicks work, ft09 broken.
- **#3(queue) [Architecture] Qwen3-32B** — Exp 003: reverted. 2x slower, same score.
- **#5(queue) [Exploration Strategy] No LLM calls** — Exp 004: reverted. 12x faster (1.4s) but still 0 score.
- **#6(queue) [Exploration Strategy] BFS to frontier** — Exp 005: reverted. Better navigation but no score (24s).
