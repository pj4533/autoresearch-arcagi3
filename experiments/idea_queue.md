# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, post exp 008): Pure programmatic exploration has hit its ceiling. vc33 has a LIFE MECHANIC — wrong clicks drain lives → GAME_OVER. ls20 state space is enormous (100 actions = 100 unique states). Brute-force won't work — the agent needs INTELLIGENCE. Two paths forward: (1) validate with a strong cloud model (Claude Sonnet) to check if any agent can score, (2) use LLM strategically at key decision points (not every step, but to analyze grid and plan clicks).**

---

### 1. [Architecture] Cloud model validation — can ANY agent score?
- **Hypothesis**: After 8 stategraph experiments and 30 explorer experiments all scoring 0, we need to validate whether the FRAMEWORK works at all. Claude Sonnet 4.5 is a proven strong reasoner. Running it on a single game answers: if Claude scores > 0, the issue is model intelligence → focus on better models or code-generation. If Claude also scores 0, there's a framework/game bug that no amount of strategy can fix. This is the single most important experiment to run next — it determines the entire strategic direction.
- **Files to modify**: None — CLI args only
- **Changes**: Run `uv run python run_benchmark.py --agent explorer --config claude-sonnet-4-5-20250929-thinking-8k --max-actions 40 --games vc33-9851e02b`. Single game (vc33 since clicks work). Cost: ~$0.50-2.00.
- **Expected impact**: Either validates framework (Claude scores > 0, meaning we need better reasoning) OR reveals framework bug (Claude also scores 0, meaning the game/API pipeline is broken).

### 2. [Exploration Strategy] VC33 smart clicking — avoid life-draining clicks
- **Hypothesis**: Exp 006-008 revealed vc33 has a life mechanic: wrong clicks consume lives and the game ends in GAME_OVER. Brute-force clicking kills the agent before finding the winning sequence. The fix: track which clicks drain lives (score or state changes negatively) and AVOID repeating those patterns. Only click objects that produce "safe" changes (frame changes without life loss).
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. After each click, check if `result_state` indicates GAME_OVER or if a "lives" indicator changed
  2. If a click at object type X (by color/size) caused life loss, mark that object category as DANGEROUS
  3. In `_try_click()`, skip objects in dangerous categories
  4. Track the game's "remaining lives" indicator (probably in the status bar) — if low, only click objects that previously produced positive changes
  5. If GAME_OVER occurs, record which click sequence led there and avoid it in the next game
- **Expected impact**: Prevents wasting lives on structural/non-interactive objects. Focuses clicks on objects that produce positive state changes without draining lives.

### 3. [Architecture] VC33 LLM-guided first click — use model to analyze grid ONCE
- **Hypothesis**: Pure programmatic exploration can't solve vc33 because it can't distinguish interactive buttons from decorative objects. But calling the LLM every step is wasteful. The sweet spot: call the LLM ONCE at the start to analyze the grid and identify likely interactive objects. The LLM sees the grid (as text matrix), identifies colored objects, and suggests which to click. Then programmatic exploration tries those targets first.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. At step 0, call LLM with grid + prompt: "This is a click puzzle. Identify the interactive objects. Which objects look like clickable buttons? Describe their positions, colors, and likely function."
  2. Parse LLM response for suggested click targets
  3. Add these to front of click_queue with highest priority
  4. Execute programmatically from there
  5. If score increases, call LLM again with new grid to identify next set of targets
- **Expected impact**: One LLM call (~1-2s) gives the agent intelligent targeting. Combines programmatic speed with LLM reasoning for initial analysis. Cost: 1 LLM call per game instead of 40.

### 4. [Architecture] Code-generation approach (Symbolica-style)
- **Hypothesis**: Symbolica scored 36.08% on ARC-AGI-3 by having LLM write Python code to play games, not by choosing actions. One cloud API call generates a strategy function, then the function runs for 100+ actions at zero cost. This fundamentally different approach uses LLM intelligence for STRATEGY (what to do) and programmatic execution (doing it fast). With Claude Sonnet analyzing the grid structure and writing a grid-analysis function, the agent can identify interactive objects programmatically.
- **Files to modify**: New agent or stategraph modification
- **Changes**: At step 0, call Claude Sonnet with:
  - Grid as text matrix
  - Available actions
  - Game mechanics description (click puzzle, limited lives)
  - Ask: "Write a Python function `def analyze_grid(grid) -> list[tuple[int,int]]` that identifies likely interactive objects to click, sorted by priority."
  - Execute the generated function on each new grid state
  - Cost: ~$0.05 per game
- **Expected impact**: Leverages cloud model intelligence for analysis strategy while keeping per-action cost zero.

### 5. [Exploration Strategy] VC33 click-effect tracking — learn which objects are interactive
- **Hypothesis**: In exp 006-007, the agent clicked many objects and some produced 265 cell changes. Instead of treating all clicks equally, track which specific object types (by color, size, position) produce real frame changes vs no change vs life loss. After the first pass, ONLY click objects that are confirmed interactive.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. First pass (Phase 1): Click one object of each color/size category, recording effect
  2. Categorize each click as: "interactive" (large frame change), "decorative" (no change), or "dangerous" (life loss/game over)
  3. Second pass (Phase 2): Only click "interactive" objects, trying different combinations
  4. Track which click SEQUENCES produce score increases
- **Expected impact**: Reduces wasted clicks from ~90% to ~10%. Focuses remaining life budget on truly interactive objects.

### 6. [Exploration Strategy] LS20 LLM-guided navigation — analyze map structure
- **Hypothesis**: ls20 has 100 unique states in 100 actions — the state graph is useless. But the LLM CAN analyze the grid to see the map structure: walls, paths, objects, player position. Instead of random exploration, call the LLM every 10-15 steps with the current grid and ask "Where should the player go? What objects are visible? Plan a path." The LLM provides directional guidance, the agent executes 10-15 moves, then re-checks.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: For ls20 (detected by available_actions = ACTION1-5):
  1. Every 10 steps, send grid to LLM
  2. LLM identifies: player position, visible objects, wall structure, goal direction
  3. LLM suggests: "Move right 5 times, then down 3 times to reach the key"
  4. Execute the plan programmatically
  5. Re-check with LLM after plan completion
- **Expected impact**: Purposeful navigation instead of random exploration. The LLM provides the "where to go" intelligence, programmatic execution provides speed.

### 7. [Architecture] Hybrid approach — programmatic speed + LLM at key decision points
- **Hypothesis**: Pure LLM (explorer) is too slow. Pure programmatic (stategraph) is too dumb. The sweet spot: programmatic exploration for the bulk of actions, LLM called at KEY moments: (a) when a new state type is discovered, (b) when the agent gets stuck, (c) every N actions for strategic guidance. The 3rd-place solution used no LLM and solved 12 levels — but it had 8 hours. We need LLM intelligence to compensate for our smaller time/action budget.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Run programmatically by default (0.012s/action)
  2. Call LLM when: (a) first seeing a game, (b) score increases (new level), (c) after 50 actions with no progress, (d) when a click produces a large frame change
  3. LLM analyzes accumulated state graph + current grid
  4. LLM suggests: specific targets, strategy shift, or grid analysis
  5. Resume programmatic execution with LLM guidance
- **Expected impact**: Best of both worlds: programmatic speed for bulk exploration + LLM intelligence at decision points.

### 8. [Preprocessing] Rule-based status bar detection for stategraph
- **Hypothesis**: Our stategraph masks fixed 2 rows top/bottom. Dynamic detection via connected components (segments touching edges with >5:1 aspect ratio) would be more robust.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Detect status bars via flood fill + edge proximity + aspect ratio checks.
- **Expected impact**: Better state hashing for ls20 where status bar changes create false unique states.

### 9. [Exploration Strategy] VC33 targeted click test — known sprite positions
- **Hypothesis**: From game code analysis, vc33 level 1 has interactive sprites at grid positions (30,12) and (30,16) → agent coords (60,24) and (60,32). Before implementing complex strategies, test if clicking EXACTLY at these known positions produces a score. If it does, the issue is targeting. If not, the issue is deeper.
- **Files to modify**: Hardcode test or manual arc CLI test
- **Changes**: Run `arc start vc33 --max-actions 10` then `arc action click --x 60 --y 24`, `arc action click --x 60 --y 32`, check if score changes. This is a 30-second diagnostic.
- **Expected impact**: Confirms whether the win sequence is achievable with correct targeting, or if there's a game-level issue.

### 10. [Exploration Strategy] LS20 object detection + pathfinding
- **Hypothesis**: LS20 has keys, doors, rotators, health. Detect via connected components, implement A* pathfinding to targets.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Identify player, keys, doors by color/size. A* to nearest target.
- **Expected impact**: Direct navigation vs random exploration.

### 11. [State Tracking] VC33 life counter tracking — preserve lives
- **Hypothesis**: vc33's life mechanic means the agent needs to conserve clicks. Track the life counter (probably in the status bar) and stop exploring when lives are low. Only use remaining lives on confirmed-interactive objects.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Detect life counter region in status bar. Parse remaining lives. When lives ≤ 2, switch to conservative mode: only click previously-confirmed interactive objects.
- **Expected impact**: Prevents GAME_OVER from wasted clicks. Preserves lives for winning sequence.

### 12. [Exploration Strategy] UCB1 action selection
- **Hypothesis**: Use UCB1 to balance exploit vs explore. Actions that change frames get higher reward.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Track per-action rewards. frame_changed=1, score_increase=10. Pick highest UCB1.
- **Expected impact**: Smarter selection.

---

## Completed

- **#1 [Prompt Engineering] Game-type-aware system prompt** — Exp 002: reverted (score=0.0000).
- **#2 [Exploration Strategy] Fix three hardcoded Move Up fallbacks** — Exp 003: reverted (score=0.0000).
- **#3 [Exploration Strategy] Programmatic click probe** — Exp 004: reverted (score=0.0000).
- **#4 [Prompt Engineering] Eliminate convert LLM call** — Exp 005: reverted (score=0.0000).
- **#27 [Prompt Engineering] Disable Qwen thinking mode** — Exp 006: ACCEPTED (foundational fix).
- **#5-#16 (explorer experiments)** — All reverted. See log_archive_explorer.md.
- **fix [Bug Fix] Frame comparison timing** — Exp 022: ACCEPTED.
- **Stategraph 001**: Baseline — 120 actions in 17s, score 0.
- **Stategraph 002**: Click diagnostic — vc33 clicks work, ft09 broken.
- **Stategraph 003**: Qwen3-32B — 2x slower, same score. Reverted.
- **Stategraph 004**: No LLM — 12x faster (1.4s), same score. Reverted.
- **Stategraph 005**: BFS to frontier — better navigation, same score. Reverted.
- **Stategraph 006**: 5-tier priority + 200 actions — vc33 GAME_OVER from life loss. Reverted.
- **Stategraph 007**: Click cache clear + no LLM — 600 actions in 6.6s, still 0. Brute-force can't solve puzzle logic. Reverted.
- **Stategraph 008**: 500 actions deep — 1500 in 20s. ls20: 100 unique states. vc33: GAME_OVER. Pure exploration insufficient. Reverted.
