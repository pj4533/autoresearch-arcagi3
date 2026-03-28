# Research Notes

Accumulated knowledge from experiments. Never wiped, only appended.

## Key Insights

### Initial Agent Analysis (2026-03-27)

**Agent Architecture**: 3-phase Probe → Explore → Exploit (but exploit is never entered).

**Critical Weaknesses Identified:**

1. **Double LLM call per action**: Every explore step calls the LLM twice — once for reasoning (explore prompt) and once to convert "Move Up" → "ACTION1" (convert prompt). This halves throughput. Priority #1 to fix.

2. **No click probing**: Probe phase only tests ACTION1-5 (movement + perform). Games ft09 and vc33 rely on ACTION6 (clicking) which is never probed. The agent enters explore phase blind to clicking mechanics.

3. **Weak frame change description**: `_describe_frame_change` only returns "N cells changed (X% of grid)" — no information about WHAT changed (colors, positions, directions). The LLM can't reason well about game mechanics with so little information.

4. **Generic system prompt**: Same prompt for all 3 games despite radically different mechanics (ls20 = movement navigation, ft09 = click to toggle colors, vc33 = click-only reasoning).

5. **Flat unstructured memory**: Memory is an append-only string truncated to 15 lines. No distinction between confirmed facts and tentative hypotheses.

6. **Exploit phase never used**: Code defines PHASE_EXPLOIT constant but the step() dispatcher only has probe and "else" (explore). When the agent knows the answer, it still pays LLM cost per action.

7. **No loop detection**: No mechanism to detect when the agent is revisiting the same grid state.

8. **No cross-level transfer**: When moving to a new level, all accumulated knowledge is lost.

9. **No score tracking**: Agent doesn't explicitly track which actions caused score changes.

**Game-Specific Notes:**
- **ls20**: Uses ACTION1-5 (movement + perform). Navigation with hidden state. Probe phase is well-suited.
- **ft09**: Uses ACTION6 (click) + ACTION5 (perform). Click toggles colors (9→8). Multiple levels. Probe phase misses clicking entirely.
- **vc33**: ONLY uses ACTION6 (click). Movement actions are not available. Probe phase is completely useless since it only tests movement.

**Priority Analysis:**
- Ideas 1-4 are highest priority: they fix fundamental architectural weaknesses.
- Ideas 5-8 are medium priority: they improve strategy quality.
- Ideas 9-20 are lower priority: they add capabilities that build on the above.

### Category Coverage in Initial Queue
- Prompt Engineering: #1, #4, #15 (3 ideas)
- Exploration Strategy: #2, #8, #14 (3 ideas)
- State Tracking: #3, #9, #10 (3 ideas)
- Phase Transitions: #7, #11, #19 (3 ideas)
- Memory Management: #5, #13, #16 (3 ideas)
- Preprocessing: #12, #17, #20 (3 ideas)
- Action Sequencing: #6, #18 (2 ideas)

All 7 categories covered. Balanced distribution.

### Competition Research Findings (2026-03-27)

**ARC-AGI-3 Preview Competition Results (Aug 2025):**
- 1st: StochasticGoose (12.58%) — CNN + RL predicting frame-changing actions
- 2nd: Blind Squirrel (6.71%) — Directed state graphs with value-ranked action pairs
- 3rd: Graph-based exploration (training-free, solved 12 private levels)
- Best LLM approach: Tomas Engine (3.70%), crashed often
- Current frontier models (March 2026): All below 1%. Gemini 3.1 Pro tops at 0.37%.

**Key Takeaway**: Structured exploration and state tracking crushingly beat pure LLM reasoning.

**Most Actionable Strategies from Research:**

1. **State Graph Construction** (2nd/3rd place): Build directed graph where nodes = hashed grid states, edges = actions. Provides loop detection, shortest-path replay, frontier tracking. Single highest-impact change.

2. **Click Target Filtering** (1st place insight): Most cells are background/empty. Identifying interactive objects and only clicking those transforms the 4096-cell search into a ~10-50 target problem.

3. **StateAct Structured State Tracking** (academic research): Requiring explicit state tracking at each step reduced average steps from 31.49 to 19.11 (39% reduction). Outputs: current state summary, changes, mechanics discovered, goal hypothesis, untested approaches.

4. **ReflAct Goal Reflection** (academic research): "What is my current state relative to my goal?" prompting improved success rates by 21-28%.

5. **Cross-Level Budget Allocation**: Scoring formula weights later levels more. Optimal strategy: invest ~60% of action budget in exploration on levels 1-2, then exploit efficiently on levels 3+.

6. **Visual Object Prioritization for Clicks** (graph-based approach): Segment frame into connected components. Prioritize larger, more colorful, more morphologically distinct objects. Five priority tiers.

7. **Curiosity-Driven Exploration**: Prioritize actions whose outcomes are least predictable (highest information gain). Build forward model: "if I do X in state S, I expect S'". When result differs, that's the most valuable learning.

**Sources Reviewed:**
- ARC Prize 2025 Results and Analysis (arcprize.org)
- ARC-AGI-3 Technical Report (arxiv 2603.24621)
- 1st Place Write-up StochasticGoose (medium.com)
- Graph-Based Exploration for ARC-AGI-3 (arxiv 2512.24156)
- StateAct: Self-prompting and State-tracking (arxiv 2410.02810)
- ReflAct: World-Grounded Decision Making (arxiv 2505.15182)
- LPLH: Learning to Play Like Humans (arxiv 2505.12439)
- ICM: Curiosity-driven Exploration (Pathak et al.)

**Updated Queue Priorities (after research):**
- Inserted State Graph Construction at #2 (highest-impact new idea)
- Inserted StateAct prompting at #5
- Inserted Click Target Filtering at #7
- Inserted ReflAct Goal Reflection at #11
- Queue now has 22 ideas across all 7 categories

### Updated Category Coverage
- Prompt Engineering: #1, #5, #6, #11 (4 ideas)
- Exploration Strategy: #3, #12, #20 (3 ideas)
- State Tracking: #2, #4, #13 (3 ideas)
- Phase Transitions: #10, #14, #17 (3 ideas)
- Memory Management: #8, #15, #18 (3 ideas)
- Preprocessing: #7, #16, #19, #22 (4 ideas)
- Action Sequencing: #9, #21 (2 ideas)

### ADCR Agent Analysis (2026-03-27)

Studied the reference ADCR agent to identify proven patterns the Explorer agent should adopt.

**Patterns ADCR Uses That Explorer Lacks:**

1. **`---` Divider Pattern**: ADCR gets analysis AND memory update in ONE LLM call by using a `---` separator. The model writes analysis above the divider and memory scratchpad below it. Explorer currently doesn't combine outputs — this is a free efficiency win.

2. **Multi-Turn Message History**: ADCR includes the previous prompt and the model's previous response as conversation history. This gives the model continuity between steps. Explorer sends fresh single-message prompts each time with no conversation context.

3. **"NEW LEVEL!!!!" Positive Reinforcement**: ADCR detects score increases and tells the model "Whatever you did must have been good!" Explorer provides no feedback when score changes. This is important for the model to learn what works.

4. **image_diff() Visual Highlighting**: ADCR sends a diff-highlighted image showing what changed between frames. Explorer only counts changed cells as text. The `image_diff()` utility already exists in the codebase.

5. **JSON Retry Mechanism**: ADCR retries JSON parsing twice before falling back. Explorer immediately falls back to ACTION1 on first failure, wasting the action.

6. **Dynamic Action Examples in Prompts**: ADCR builds example actions from available_actions list. Explorer's prompts are more static.

7. **Movement-First Guidance**: ADCR explicitly instructs "favor moves before clicking." Explorer has no such guidance.

8. **Word-Limited Memory**: ADCR enforces memory_word_limit properly. Explorer truncates by line count (15 lines) which is crude.

**Utility Code Findings:**

- **FrameGrid**: `List[List[int]]`, values 0-15, typically 64x64
- **Click coordinates**: 0-127 range (divided by 2 internally → maps to 64x64 grid)
- **grid_to_text_matrix**: Just `json.dumps(grid)` — very compact but no spatial structure
- **extract_json_from_response**: Robust — tries fenced blocks, brace matching, control char cleanup
- **image_diff(img_a, img_b)**: Highlights changed pixels — available but Explorer doesn't use it
- **16-color palette**: 0=white, 5=black, 8=red, 9=blue, 11=yellow, etc.
- **get_human_inputs_text()**: Utility function for formatting action descriptions — exists but unused by Explorer

**New Ideas Generated from ADCR Analysis:**
- Added #23: Adopt `---` divider for combined analysis+memory
- Added #24: Score change feedback ("NEW LEVEL" reinforcement)
- Added #25: Multi-turn conversation context
- Added #26: Use image_diff() for visual change highlighting

### Diagnostic Analysis of Prior Experiments (2026-03-27)

**CRITICAL FINDING: ALL 95+ prior experiments scored 0 across all 3 games. The agent has NEVER completed a single level.**

Analyzed action traces from exp_001 (baseline) and exp_095 (latest):

**VC33 (click-only game) — CATASTROPHIC FAILURE:**
- Agent sends 100% movement actions (Move Down, Move Right, Move Up)
- VC33 ONLY supports ACTION6 (click) — all movement actions are invalid/no-ops
- Probe phase skipped (correct: no ACTION1-5 available) but explore phase defaults to movement
- Root cause: LLM ignores available_actions list, defaults to movement. Convert fallback is hardcoded ACTION1.
- The agent never clicks a single time in VC33.

**FT09 (pattern completion with clicking) — BROKEN:**
- 84% Move Down actions in exp_095 (21 of 25 actions)
- FT09 needs clicking to toggle colors (9→8) then Perform to submit
- Agent tries movement first, rarely clicks, never discovers toggle mechanic
- Only 3-4 click attempts across 25 actions in baseline, and they don't target meaningful cells

**LS20 (navigation) — STUCK IN LOOPS:**
- 68% Move Down in exp_095 (17 of 25 actions)
- Agent stuck in "5-colored region at bottom-left (rows 40-45, cols 2-5)" for ALL 25 actions
- Observations identical across 20+ actions: same description, same grid region
- No loop detection, no strategy change, no diversification

**Root Causes Identified:**
1. **LLM bias toward movement**: Qwen model defaults to "Move Down" regardless of game type
2. **Weak action constraint communication**: Available actions listed in prompt but model ignores them
3. **Broken convert fallback**: Hardcoded `ACTION1` fallback sends invalid actions for click-only games
4. **No stuck detection**: Agent repeats same action indefinitely with no progress signal
5. **No game-type awareness**: Same generic strategy for navigation vs. clicking vs. reasoning games
6. **Insufficient click exposure**: Probe never tests clicking, explore rarely suggests it

**Queue Reprioritization:**
- Moved game-type-aware prompt to #1 (fixes VC33 catastrophic failure)
- Added convert fallback fix as #2 (prevents invalid fallback actions)
- Probe clicking at #3 (enables click discovery)
- Loop detection at #5 (breaks LS20 stuck pattern)
- Stuck detection at #9 (forces strategy change after N failed actions)

**Game Structure from Data Analysis:**
- LS20: 7 levels, baseline actions [29, 41, 172, 49, 53, 62, 82]
- FT09: 6 levels, baseline varies
- VC33: 7 levels, baseline varies
- Grid: 64x64, 16 colors (0-15)
- Click coordinates: 0-127 (scaled 2x from grid coords)
- Max actions per experiment: 25 (old system), 40 (new system)

### Qwen 3.5-35B Model-Specific Findings (2026-03-27)

**Critical: No KV Cache Reuse on MLX**
- Qwen3.5-35B-A3B has a hybrid DeltaNet + attention architecture (3:1 ratio)
- The DeltaNet layers use recurrent SSM state that CANNOT be cached
- **Every inference call recomputes the full prompt from scratch**
- This means prompt length directly impacts latency on EVERY step
- Source: ml-explore/mlx-lm#980

**Implication**: Prompt compression is way more important than for cloud models. Every saved token reduces wall time per action. Current ~14.5 sec/action could be reduced significantly with shorter prompts.

**Thinking Mode + JSON Issues:**
- Qwen3.5 thinking mode can leak `<think>` tags into JSON output (documented bug)
- Structured output does NOT work in thinking mode per Alibaba docs
- Recommendation: Disable thinking for convert/JSON calls, keep for reasoning
- Our MLX adapter strips `<think>` tags but doesn't disable thinking at template level

**Token Efficiency Recommendations:**
- Per-step max_tokens: 128 for convert, 512-1024 for explore (not blanket 4096)
- Lower temperature for structured output (0.1-0.3) vs reasoning (0.6-0.7)
- Abbreviate repetitive context after first introduction
- Hard character limits on memory/hypothesis sections

**Model Comparison Opportunity:**
- Qwen3-32B dense DOES support KV cache reuse (standard attention throughout)
- Despite slower raw tok/s (20-30 vs 60-70), effective throughput may be better for multi-turn because prompt doesn't recompute from scratch
- Worth benchmarking head-to-head

**Qwen Strengths for Our Use Case:**
- 76.5 on IFBench (best instruction following among open models)
- Strong agentic capabilities (78.6 on BrowseComp)
- Follows detailed, structured prompt instructions reliably
- JSON output from markdown code blocks works well

**Qwen Weaknesses:**
- High hallucination rate (~80-82% on AA-Omniscience for smaller variants)
- Confidently asserts incorrect hypotheses — need explicit uncertainty permission
- No vision via MLX (text-only, is_multimodal: false)

### Game Mechanics Deep Dive (2026-03-27)

**Baseline Actions Per Level (from metadata.json):**

| Game | Levels | Baseline per level | Total | Easiest level |
|------|--------|--------------------|-------|---------------|
| VC33 | 7 | [6, 13, 31, 59, 92, 24, 82] | 307 | Level 1: 6 clicks |
| FT09 | 6 | [15, 7, 15, 16, 21, 17] | 91 | Level 2: 7 actions |
| LS20 | 7 | [29, 41, 172, 49, 53, 62, 82] | 488 | Level 1: 29 moves |

**Scoring with 40 Max Actions:**
- Score = max(0, 1 - agent_actions / (3 * baseline))
- VC33 level 1: Human solves in 6 clicks. Agent gets score > 0 if solved in < 18 clicks.
  - If solved in 6 clicks: score = 0.667
  - If solved in 12 clicks: score = 0.333
- FT09 level 2: Human solves in 7 actions. Agent can use up to 21 actions.
- LS20 level 1: Human uses 29 moves. Agent can use up to 87.

**Key Insight**: Solving even ONE level would be a breakthrough. VC33 level 1 is the easiest target (6 baseline clicks). With 40 total actions budget, agent could solve levels 1+2 of VC33 (19 baseline, 57 allowed).

**VC33 Game Mechanics (from source code):**
- ONLY handles ACTION6 (click) — `action.id.value == 6`
- Click converts display coordinates to grid coordinates via camera
- Two clickable sprite types:
  - Sprites tagged "ZGd" → interactive click handler
  - Sprites tagged "zHk" → conditional check + animation
- Level completes when `gug()` returns True → `next_level()`
- Loss condition exists (limited clicks via `vrr.olv`)
- Sprites are colored blocks on the grid — agent must identify which blocks to click

**FT09 Mechanics (from source code):**
- **ONLY clicking matters** — movement and perform are no-ops. Only ACTION6 (click) changes game state.
- **3x3 toggle pattern**: Clicking a cell changes colors in a 3x3 neighborhood around it. Different cells have different toggle masks.
- **Color cycling**: Colors cycle through a palette list (not just 9→8). Each click advances the color index by 1.
- **Level completion**: All target sprites must match their target colors. `cgj()` checks this.
- **Loss condition**: Limited moves/lives per level (`lpw.lph()`).
- **Strategy**: This is a constraint satisfaction problem. Agent needs to: (1) discover toggle patterns by clicking and observing, (2) identify target colors, (3) plan click sequence to match targets.
- **Available actions include ACTION1-6** but only ACTION6 does anything. CLAUDE.md says "perform to submit" but ACTION5 is actually a no-op.

**LS20 Known Mechanics:**
- Navigation with hidden state — directional moves shift elements
- Available actions: ACTION1-5 (movement + perform)
- Has hidden state mechanics that aren't visible in the grid
- 172 baseline actions for level 3 indicates very complex navigation

**Strategy Implications:**
1. **VC33 is the quickest win** — level 1 needs only 6 clicks. If the agent can identify what to click, it scores immediately.
2. **FT09 level 2 is also quick** — 7 actions baseline.
3. **LS20 is hardest** — level 1 needs 29 moves minimum, and the agent can't even navigate without getting stuck.
4. **Priority order for getting first score**: VC33 > FT09 > LS20.

**MLX Adapter Notes (from code review):**
- `call_with_tracking` accepts `step_name` but doesn't pass generation params per step
- To implement per-step temperature/max_tokens, executor would need to modify the adapter
- `apply_chat_template` called with default args — no `enable_thinking=False` option
- `_strip_thinking_tags` removes `<think>` blocks AFTER generation (wasted tokens)

### Token Usage Analysis (2026-03-27)

Analyzed token counts from prior experiments to understand prompt overhead.

**Average tokens per action (across experiments):**

| Game | Prompt Tokens | Completion Tokens | Total | Seconds/Action |
|------|--------------|-------------------|-------|----------------|
| LS20 | 8,000-8,400 | 700-960 | ~9,000 | 14.6-17.4s |
| FT09 | 7,800-19,500 | 470-570 | ~8,300-20,000 | 12.6-21.5s |
| VC33 | 9,800-10,100 | 820-1,140 | ~10,600-11,200 | 16.8-20.8s |

**Key findings:**
- Prompt is 10-40x larger than completion. With no KV cache, ALL prompt tokens are reprocessed every action.
- A 64x64 grid as JSON is ~8,000 tokens alone — this is the floor.
- FT09 can balloon to 19,500 prompt tokens in some experiments (exp_089) — likely from accumulating observation text.
- Completion tokens rarely exceed 1,200 — the max_completion_tokens of 4096 is 3-4x too high.
- At 40 max actions, one game takes 8-14 minutes. Full 3-game benchmark: 24-42 minutes.

**Optimization opportunities (from token data):**
1. **Lower max_completion_tokens to 1500** — No lost content, prevents runaway generation.
2. **Compress grid representation** — Sending only non-background regions could cut 8,000 to ~2,000 tokens.
3. **Cap observation/memory text** — Prevent the balloon seen in FT09 exp_089 (19.5k tokens).
4. **Eliminate convert call (#4)** — Saves ~8,000-10,000 prompt tokens per action (entire second call).

**Speed impact of #4 (eliminate convert call):**
- Each convert call costs ~8,000 prompt tokens (system prompt + frame + action list).
- At ~60-70 tok/s prompt processing, that's ~2-3 seconds of pure prompt processing saved.
- Plus ~500 completion tokens at ~60-70 tok/s = ~0.5 seconds.
- Total: ~3-4 seconds saved per action, plus eliminating parse failure risk.
- Over 40 actions: ~2-3 minutes saved per game.

### ARC-AGI-3 Game Mechanics & Strategy Deep Research (2026-03-27)

**CRITICAL: Scoring is QUADRATIC, not linear!**
- Per-level: score = min(1.0, human_actions / agent_actions)^2
- 3x human actions = (1/3)^2 = **11% score**, not 33%
- 10x human actions = **1% score**
- Later levels weighted MORE: Level 1 = 1/15 weight, Level 5 = 5/15 weight
- Every RESET counts as an action
- This means action efficiency has exponential returns. Reducing from 30 to 15 actions quadruples the score.

Note: CLAUDE.md uses a simplified formula `max(0, 1 - agent/(3*human))`. The actual RHAE scoring from the technical paper is quadratic with level-weighted averaging.

**Game-Specific Mechanics (from technical paper + competition docs):**

- **LS20**: Map navigation with symbol transformations. Arrow-key controlled. **Has a three-life mechanic** — some actions can kill the agent! Level 1 has 355 possible states. Levels 8+ have partial observations (hidden/"latent" state). Recently upgraded with additional mechanics.

- **FT09**: Click-based pattern completion. Toggle colors (9→8) in answer grid. Patterns occasionally **overlap on screen**. Levels 6+ have extremely large state spaces.

- **VC33**: Volume/height adjustment — **alternate volume of objects to match target heights**. Visual salience aligns well with interactive elements. Level 6 needs ~10x level 1 actions (50 vs <5).

**CRITICAL: Status Bar Masking for State Graph**
- The game displays a status bar (step counter) that changes EVERY step
- Without masking the status bar region before hashing, every frame looks unique
- State graph (#6 in queue) WILL NOT WORK without status bar masking
- Must identify the status bar region and exclude it from grid hashing
- This is a prerequisite for idea #6 — executor must implement this

**Competition Throughput Analysis:**
- LLM agent at 14.5s/action: ~165 actions in 40 minutes
- Non-LLM agents: 96,000+ actions in 8 hours (580x advantage)
- 1st place (RL): trained on binary "did action change frame?" signal
- 3rd place (graph): pure programmatic exploration, no learning, beat ALL LLMs
- Pure LLM approaches scored <1% — "underperforms even a random policy"

**Key Strategic Insight from Competition:**
The ideal hybrid architecture should be:
1. **Programmatic layer**: Frame hashing, state graph, action filtering, loop detection, frame diffing
2. **LLM layer**: Hypothesis formation, goal inference, strategy — called RARELY, not every step

Current agent calls LLM on every step. This is fundamentally wrong for efficiency.

**New Ideas from This Research:**
- Status bar masking (prerequisite for state graph)
- Hypothesis-driven probing (ask LLM "what to test?" not "what to do?")
- ACTION7 (undo) should be tested in probe phase
- Reduce LLM call frequency (every 3-5 actions, not every action)

### Executor Baseline Benchmark (2026-03-27, post-infrastructure fix)

The executor fixed the MLX adapter (sampler API) and benchmark runner (game IDs). First successful benchmark run on LS20:

**Results (LS20, 40 max actions):**
- Score: 0, State: NOT_FINISHED, Actions: 40, Duration: 2047s (34 min)
- Action distribution: ACTION1 (Move Up) = 27 (67.5%), ACTION2 (Move Down) = 10 (25%), ACTION3/4 = 3
- Tokens: 748k prompt (avg 18,700/action), 111k completion (avg 2,779/action)
- Time per action: ~51 seconds

**Comparison to old experiments:**
- Old: ~14.5s/action, ~8,300 prompt tok/action, ~700 comp tok/action
- New: ~51s/action, ~18,700 prompt tok/action, ~2,779 comp tok/action
- Completion tokens 4x higher — likely thinking mode generating ~2000 tokens/action that get stripped after generation. At 60-70 tok/s, this is ~30 seconds of WASTED inference per action.
- Thinking tokens waste: ~30s × 40 actions = **~20 minutes wasted per game on thinking tokens that are discarded**

**Confirms:**
- Infrastructure works (benchmark completes, 40 max_actions)
- Agent behavior unchanged (still loops Move Up/Down, score 0)
- Thinking mode waste is even bigger than estimated — idea #27 (disable thinking for convert/JSON) is more urgent
- Ideas #1-3 (game awareness, convert fallback, click probe) not yet implemented

**Third baseline run (224617, LS20):** 40 actions, 47.3 min, 71s/action. 80% Move Up. Score 0.

**FT09 baseline (231647):** 32 actions (GAME_OVER — lost!), 37 min, 55.5s/action. **100% ACTION1 (Move Up)** — every single action was Move Up in a click-only game. No probe phase, no clicking. Game ended in GAME_OVER.

**VC33 baseline (000347):** 40 actions, 40.3 min. 39 ACTION1 + 1 ACTION6. LLM sometimes says "Click at (50,55)" but convert maps it to ACTION1 — CONFIRMS the direct-mapping bug. Only 1 of ~3 click attempts became actual ACTION6.

**Exp 002 results (ideas #1 + #2 partial — reverted):**
- LS20: Score 0, 40 actions, 71.7s/action. ACTION1=31 (77.5%). JSON parse 17%. Similar to baseline.
- FT09: Score 0, 40 actions, 85.9s/action. **ACTION1=25 (62.5%), ACTION6=15 (37.5%)**. JSON parse 20%. Clicks went 0% → 37.5%.
- VC33: Score 0, 40 actions, 68.5s/action. **ACTION1=29 (72.5%), ACTION6=11 (27.5%)**. JSON parse 18%. Clicks went 2.5% → 27.5%.
- **REVERTED**: Executor reverted changes because JSON still malformed ("..." literal in values) and slower due to longer prompts.
- **Verdict**: Game-type prompts work directionally but can't overcome 80% JSON parse failure. Thinking mode fix (#27) is the gating issue.

**Executor now implementing idea #2 (all 3 bugs):**
- Bug 1: Explore parse fallback uses available[0], ACTION6 gets center coords (64,64) ✓
- Bug 2: Convert direct mapping checks `direct in available` ✓
- Bug 3: Convert final fallback uses available[0] ✓
- Combined with #1 (game-type prompts, currently reverted): When re-applied together with #2, even parse failures will use valid actions.

**Exp 003 results (idea #2 — fallback fixes, partial results so far):**
- FT09 (043645): Score 0, 40 actions, 131s/action (!). **ACTION6=34 (85%), ACTION1=6 (15%)**. JSON parse 28%. Clicks went from 0% → 85%! But 131s/action is terrible (double the previous). Each action hits TWO LLM calls (explore + convert) because the fallback outputs "ACTION6" which the convert direct mapping doesn't recognize as a human-readable action.
- Score still 0: clicking center (64,64) repeatedly doesn't solve puzzles. Need targeted clicking.
- The 15% remaining ACTION1 are from convert failing to map "ACTION6" string to the right game action.
- **Speed issue**: 131s/action = 87 min per game. 3 games = ~4.4 hours per experiment. Untenable.
- **Confirms**: #4 (eliminate convert call) and #27 (disable thinking) both urgently needed for speed.
- VC33 (054925): Score 0, 40 actions, 108.9s/action. **ACTION6=30 (75%), ACTION1=10 (25%)**. Clicks went 2.5% → 75%. But clicking center (64,64) doesn't hit any interactive objects — score unchanged. Need targeted clicking (#3, #5, or #32).

**Exp 003 summary**: Fallback fixes dramatically improved action VALIDITY (VC33: 2.5→75% clicks, FT09: 0→85%) but not TARGETING. All click-game clicks go to center (64,64). Two paths to first score:
  - Path A: Programmatic click probe (#3) → finds real objects → clicks them
  - Path B: Disable thinking (#27) → JSON parse rate 80%+ → game-type prompt works → LLM picks targets
  - Path C: Brute-force VC33 scan (#32) → no LLM, click all non-background objects

**Executor implementing idea #3 (programmatic click probe):**
- `_detect_objects()`: BFS connected components, background = most common color, sorted by size
- `_click_probe_step()`: Click each object center sequentially, no LLM calls, re-scans on score increase
- Coordinate conversion: `col * 127 / (cols-1)` for 0-127 range
- Routes VC33 and FT09 to click probe in `_probe_step()`
- This is Path A+C combined — should be very fast (no LLM latency) and may solve VC33 level 1 outright

**Exp 004 partial results (idea #3 — click probe):**
- LS20: Score 0, 40 actions, 50s/action. Same as baseline (click probe only affects click games).
- FT09: Score 0, **40/40 ACTION6 clicks, ALL probe phase, 9 seconds total (0.2s/action)**. 650x speedup. But score 0 — randomly clicking objects doesn't solve the 3x3 toggle constraint puzzle. Need smarter targeting for FT09.
- VC33 (065536): Score 0, 40 actions, 45.8s/action. Click probe found 10 objects, clicked all. Then 30 explore actions (mostly Move Up from parse failures). **Score never changed.**
  - **Root cause: clicking wrong objects.** Detected targets include color=0 (white, size 848) and color=5 (black, size 96) which are structural/border elements, not interactive game objects. The small color=9 (blue, 16) and color=11 (yellow, 12) are more likely interactive but clicks may not have hit the exact sprites.
  - **Fix needed**: (1) Filter structural colors, (2) prioritize small objects, (3) track click effects, (4) offset coordinates.
  - Executor noted "coordinate mapping likely wrong" — need to verify grid-to-click conversion.

**Executor now implementing idea #4 (eliminate convert call):**
- Available actions show ACTION codes in prompt: "ACTION1 = Move Up"
- Explore prompt requires ACTION codes in JSON output
- When action starts with "ACTION", skips convert step entirely
- ACTION6 carries x,y coordinates through
- Prompt massively simplified: no code fences, no step-by-step, just "ONLY JSON"
- Expected: ~2x speed improvement + potentially better JSON parse rate from simpler format

**Exp 005 partial results (idea #4 — eliminate convert):**
- LS20: Score 0, 40 actions, 78.3s/action. JSON parse **8%** (WORSE than 17%!). Simpler prompt format didn't improve JSON output. Still 85% Move Up. Speed improved from 131s→78s (convert skipped) but still much slower than needed.
- **Key insight**: JSON parse rate is NOT a prompt format issue — it's thinking mode. Regardless of how we format the prompt, thinking tokens corrupt the output ~90% of the time. Idea #27 (disable thinking) is the critical path.
- FT09: Score 0, GAME_OVER, 40 actions, 56.6s/action. JSON parse 5%. Only 12.5% clicks — REGRESSED from exp 003's 85% because fallback fixes (#2) were reverted. Testing #4 in isolation fails because the explore fallback is still "Move Up".
- **Conclusion**: Individual ideas don't work in isolation. Need either: (A) combine #1+#2+#3+#4 together, or (B) fix thinking mode (#27) first which makes all prompt changes effective.

**Executor now implementing idea #27 (disable thinking mode):**
- Single line: `enable_thinking=False` in `apply_chat_template`
- Clean test: no other agent/prompt changes — baseline + thinking disabled
- This is the moment of truth: if JSON parse jumps from ~15% to 80%+, thinking mode was the root cause and ALL previous ideas become viable when re-applied
- Also includes sampler API fix from earlier infrastructure work

**RESULT: `enable_thinking=False` DID NOT WORK!**
- Completion tokens: 3513/action (baseline was 3320) — NO reduction
- JSON parse: 8% — NO improvement
- VC33: Score 0, 15% clicks, 52.8s/action

**Why it failed**: Qwen3.5 may not support `enable_thinking` in the chat template the same way Qwen3 did. The parameter is likely silently ignored. From earlier research: "Qwen 3.5 does NOT support the /think and /no_think soft switches that Qwen3 did."

**UPDATE: `enable_thinking=False` DOES WORK!** Earlier analysis was wrong — the first benchmark after the change used a stale process. Fresh process results:
- JSON parse: 8% → **72%** (9x improvement!)
- Completion tokens: 3500 → **1470/action** (58% reduction)
- Speed: 78s → **50.6s/action** (36% faster)
- This is with BASELINE agent code — no #1-#4 changes applied yet
- When combined with #1+#2+#4, should see even better results

**Exp 006 partial results (thinking disabled, baseline agent):**
- LS20: Score 0, 40 actions, 50.6s/act. JSON parse 72%. Comp 1470 tok/act.
- FT09: Score 0, 40 actions, **42s/act**. JSON parse **98%!!** **72.5% clicks** (29 ACTION6). Comp 656 tok/act. Model now targets specific cells: "Click block at row 12, col 14". Still 27.5% movement (no-ops) — needs #1 (game-type prompt) to eliminate.
- **Next step**: Re-apply #1 (game-type prompt) + #2 (fallback fixes) ON TOP of #27. With 98% JSON parse, the game-type prompt should actually work → near-100% clicking → targeted → first score.

**Exp 006 ACCEPTED — #27 is now the new baseline.** First accepted experiment!

**Executor now implementing idea #5 (click targets in prompt) on top of #27:**
- `_detect_objects()`: BFS object detection with coordinate conversion built in
- `_build_click_targets_desc()`: Labels objects A-T with color, size, click coords
- Injected into explore prompt: `"A: color=9 size=16 at click(64,32)"`
- With 98% JSON parse, LLM can now READ these targets and click accurately
- This is the combination that should produce first non-zero score

**Exp 006 VC33 result:** Score 0, 40 actions, **17.5s/act** (3x faster!). **JSON parse 100%**. ACTION6=23 (57.5%), movement=17 (42.5%). Model clicks specific targets: "Click object at row 22, col 45 (a 9)". Still 42.5% movement no-ops — needs #1 (game-type prompt) to eliminate. Score 0 likely because clicks don't land on interactive sprites (coordinate mapping or wrong targets).

**Exp 006 full summary (thinking disabled, ACCEPTED):**

| Game | JSON Parse | Clicks | Speed | Score |
|------|-----------|--------|-------|-------|
| LS20 | 72% | N/A (movement game) | 50.6s/act | 0 |
| FT09 | 98% | 72.5% | 42.0s/act | 0 |
| VC33 | **100%** | 57.5% | **17.5s/act** | 0 |

Everything improved dramatically. Next: #1 (game-type) + #5 (click targets) on this foundation.

**Exp 007 partial (idea #5 — click targets on top of #27):**
- LS20: Score 0, 40 actions, **23.0s/act** (2x faster than exp 006!). JSON 78%. Click targets don't affect LS20 (movement game). Speed gain likely from optimized prompt or reduced overhead.
- FT09 (110711): Score 0, 40 actions, 48.7s/act. JSON 95%. **95% clicks** (38 ACTION6). Click targets WORK — model uses them accurately: "Click object C (color=9 at click(13,9))". BUT stuck clicking **same target C ~10+ times in a row**. NEW BUG: click loop. Model picks one target and repeats it endlessly.
  - **Fix needed**: Track clicked targets. After N clicks on same target with no effect, remove it from list or add "You already clicked C 5 times. Try a DIFFERENT target." This is the click equivalent of the movement loop problem.
- VC33 (112022): Score 0, 40 actions, 19.6s/act. **100% clicks** (40 ACTION6). Uses diverse targets (H, C, D). BUT clicking structural objects: color=5 (black, size 96 = borders) and color=4 (off-black = frames). Same click loop pattern on target C.
  - **Three remaining issues for first score:**
    1. **Object filtering**: Skip structural colors (0, 4, 5). Prioritize small colorful objects (colors 7, 9, 11).
    2. **Coordinate mapping**: Even if right objects, clicks may not land on interactive sprites. Need to verify grid→display→game coordinate chain.
    3. **Click loop**: Track clicked targets, deprioritize after N ineffective clicks.

**Exp 008 (idea #6 — state graph with loop detection, on top of #27):**
- LS20: Score 0, 40 actions, **17.7s/act**. JSON 92%. ACTION3 (Move Left) jumped to 40% — state graph working! Model now tries untried actions when warned about revisited states. Most diverse action distribution yet.
- Implementation: status bar masking (top/bottom 2 rows), MD5 grid hash, state→action→state transitions, untried action suggestions.
- FT09 (115103): Score 0, 40 actions, 25.5s/act. 14 unique click targets (no more click loop!). But 65% Move Down — state graph diversifies but model still defaults to movement for FT09. Needs #1 (game-type prompt) to eliminate movement.
- VC33: Pending.
- **Key insight**: State graph diversifies actions within the same ACTION TYPE (tries different movements) but doesn't shift between types (movement→clicking). Need #1 (game-type prompt) for that. Best next experiment: combine #27+#1+#6.

**COORDINATE MAPPING BUG FOUND (2026-03-28):**

The base agent loop (`agent.py:507-508`) divides click x,y by 2:
```python
"x": max(0, min(int(x), 127)) // 2,
"y": max(0, min(int(y), 127)) // 2,
```

So the correct formula to click on grid cell (row, col) is:
- `click_x = col * 2` (after //2, game receives col) ✓
- `click_y = row * 2` (after //2, game receives row) ✓

Current formula: `click_x = int(avg_c * 127 / max(cols - 1, 1))` — WRONG for non-64x64 grids.

Example for VC33 (51x51 grid), cell at col=25:
- Current: 25 * 127 / 50 = 63 → game gets 63//2 = 31 (WRONG, 6 cells off)
- Correct: 25 * 2 = 50 → game gets 50//2 = 25 (CORRECT)

For 64x64 grids (LS20/FT09): both formulas happen to give similar results.
For 51x51 grids (VC33): every click is ~6 cells off target.

**THIS IS THE #1 BLOCKER FOR SCORING.** All click infrastructure works but clicks physically miss the objects.

**DEEPER INVESTIGATION (2026-03-28): Zero frame changes from 25+ random clicks**

Even stuck_random clicks at random positions (0-127) in VC33 produced ZERO visible frame changes across 25 actions. This is suspicious — random clicks should occasionally hit interactive sprites by chance.

The `_explore_step` has a potential x,y loss bug: when the LLM returns `{"action": "Click at (25,25)", "x": 50, "y": 50}`, the code extracts `human_action = result.get("action")` = "Click at (25,25)" and passes ONLY the string to `_convert_to_game_action()`. The x,y values from the LLM response are LOST. The convert step would need to regenerate x,y.

However, stuck_random clicks DO include x,y directly: `{"action": "ACTION6", "x": random, "y": random}`. These go through the base agent which does `x // 2, y // 2`. A random click at x=80, y=60 → game gets (40, 30). For VC33's 49x58 grid, this is a valid cell. But no change.

**Possible root causes:**
1. The game's `camera.display_to_grid(x, y)` may apply additional transforms
2. The local server might not be processing click data correctly
3. The x,y might not be reaching the game engine at all (data not in expected format)

**Suggested debug**: Executor should add logging in `_execute_game_action` to print the exact action_data being sent for ACTION6 clicks, and check if the game response indicates any processing.

**Also**: The coordinate formula fix (`col * 2` vs `col * 127/(cols-1)`) is still relevant for LLM-directed clicks but doesn't explain why random clicks also fail.

**Executor implementing coordinate fix + brute-force click scan:**
- `click_x = min(col * 2, 127)` and `click_y = min(row * 2, 127)` ✓ (my recommended fix!)
- New `_brute_force_click_step()`: detects non-background cells, clicks each sequentially
- New `_detect_click_targets()`: finds unique non-background positions
- Score-triggered re-scan on level completion
- This is the critical test: correct coordinates + systematic clicking of all non-background objects

**Exp 013 result: STILL score 0 despite coordinate fix + brute force click.**

10 brute_click actions (correct col*2 formula), 0 frame changes. Even with corrected coordinates, clicks don't register.

**Root cause investigation: Camera transform layer**
The game uses `camera.display_to_grid(x, y)` to convert click coordinates. The base agent sends `x // 2` (0-63 range). But the camera may apply additional transforms:
- Viewport offset (grid not at position 0,0 in display)
- Zoom/scale factor different from 1:1
- Grid padding within the 64x64 display frame

VC33 grid is 49x58 within a ~64x64 display. If there's padding (e.g., grid starts at display offset 7,3), then `col*2 // 2 = col` gives grid-relative coordinates but the camera expects display-absolute coordinates.

**Suggested debug approach:**
1. Print exact (x, y) values reaching `game_client.execute_action` for ACTION6
2. Use `arc` CLI to manually play VC33 — click known objects and see what coordinates work
3. Try clicking at the RAW grid positions the model reports (e.g., "row 22, col 54" → send x=54, y=22 WITHOUT the *2 conversion — just raw grid cell indices)
4. Try a grid of evenly spaced clicks (0, 16, 32, 48, 64, 80, 96, 112) × (same) to find where interactive sprites actually are in display space

**Exp 013 action_data confirmed x,y ARE sent correctly:**
- Action 1: x=47, y=13 (within 49x58 grid bounds) ✓
- Action 2: x=57, y=48 ✓
- All 10 brute clicks have valid coordinates reaching the game
- But result_score stays 0 through all 40 actions

**SIMPLEST DEBUG: Manual test with arc CLI:**
```bash
arc start vc33 --max-actions 40
arc state --image    # See the grid
arc action click --x 50 --y 25    # Click a visible object
arc state --image    # See if anything changed
arc end
```
This would immediately reveal: (1) Does clicking work at all in local mode? (2) What coordinates hit interactive sprites? (3) Is there a display/grid mapping we're missing?

If manual clicks work with the `arc` CLI but agent clicks don't, the bug is in how the benchmark runner sends action data. If manual clicks also fail, the bug is in the local game engine's click handling.

**CLICKABLE SPRITE POSITIONS FOR VC33 (from game source code):**

Sprites with tag "ZGd" or "zHk" are the only clickable ones:
- AEF (ZGd+zHk) at set_position(34, 24) → send click_x=68, click_y=48
- mZh (ZGd) at set_position(57, 46) → send click_x=114, click_y=92
- XTW (ZGd) at set_position(16, 14) → send click_x=32, click_y=28
- dkk (zHk) at set_position(0, 12) → send click_x=0, click_y=24
- WGb (zHk) at set_position(42, 25) → send click_x=84, click_y=50

Note: set_position(x, y) where x=column, y=row. These are the sprite TOP-LEFT corners. The sprites have varying sizes (AEF is 14x10, dkk is 12x9, etc.) so clicking anywhere within their bounding box should work.

**TEST**: Executor should try clicking EXACTLY at these positions. If they produce changes, the BFS was detecting wrong targets. If they don't, the camera transform is the issue.

Also from action_data in exp results: x=19,y=13 and x=10,y=12 were sent — these DON'T match any clickable sprite position. The agent is clicking the wrong places.

**Exp 014 partial (idea #11 — multi-action planning):**
- LS20: **4.8s/action** (27x faster than baseline!). 24/40 plan_execute (60% free). Score 0.
- FT09: 17.3s/action. 26/40 plan_execute (65% free). Score 0.
- Planning works: LLM plans 2 follow-up actions per call. Only ~13 LLM calls for 40 actions.

**Speed progression: 131s → 78s → 50s → 23s → 11.5s → 4.8s/action (27x improvement)**

**Exp 018 (idea #1 — hypothesis-driven exploration):**
- LS20: 21s/act. Most balanced action distribution ever: Right 37.5%, Left 27.5%, Up 27.5%, Down 7.5%. Model forms hypotheses: "maze navigation, agent is value 1, walls are 3". Score 0 but exploration quality much better.
- FT09: 54.9s/act. 82.5% clicks. Hypothesizes it needs to click. Score 0 (click issue).
- VC33: 25s/act. 100% clicks. Correctly identifies click-only game. Score 0 (click issue).
- Hypothesis testing IS producing meaningful theories about game mechanics. But some steps have empty hypotheses (parse failures). The approach is directionally correct.

**EXP 021: ROOT CAUSE OF ALL FAILURES FOUND — FRAME COMPARISON TIMING BUG**

`previous_grids` and `frame_grids` are IDENTICAL at `step()` time. The agent's `_describe_frame_change()` compares them and ALWAYS returns "no visible change" — not because actions have no effect, but because both variables point to the SAME frame (the post-action frame).

**This explains EVERYTHING across 21 experiments:**
- Why ALL clicks showed "no visible change" (they may have worked! we just couldn't see it)
- Why ALL movement showed "no visible change" (same bug)
- Why hypothesis testing couldn't discover rules (no observable feedback)
- Why action-effect journals were useless (all effects recorded as "no change")
- Why state graphs couldn't help (every state looked the same)
- Why coordinate fixes appeared not to work (effects happened but were invisible)

**Fix (exp 022 in progress):** Save the current frame to datastore BEFORE returning the action. On the next step, compare the saved pre-action frame to the new post-action frame. This gives the actual delta.

**IMPLICATION: Once fixed, ALL previous ideas may become viable.** The agent will finally be able to see what its actions do. Hypothesis testing, action journals, state graphs — all depend on observing effects. This is the foundational bug that blocked everything.

**Exp 022 results (frame comparison fix):**
- LS20: Frame fix WORKS! Agent sees "52 cells changed" per movement action. Model reasons about effects for the first time. Most balanced actions ever (30% L, 30% R, 25% D, 15% U). Score 0.
- FT09: Clicks STILL show "no visible change" despite frame fix. The agent correctly reports "Repeated clicks produced no visible changes." This means **clicks genuinely don't change the frame** — it's NOT a comparison bug for clicks. The click pipeline has a real issue.
- **Conclusion**: Frame fix unblocked LS20 exploration (agent can now learn from movement). Click games (FT09/VC33) have a separate infrastructure issue where ACTION6 doesn't produce frame changes. This needs game-engine-level debugging.

**Exp 009 (idea #7 — enhanced frame change description):**
- LS20: Score 0, 40 actions, **11.5s/act** (fastest ever!). Now reports color transitions and change regions.
- Frame changes now show: "12 cells changed (0.5%); colors: 5->3(x8), 4->3(x4); region: bottom-left"
- Speed keeps improving: 131s → 78s → 50s → 23s → 17s → **11.5s/act**
- Coordinate bug not yet fixed — executor testing #7 (enhanced frame changes) separately.

**Previous alternative approaches (may not be needed now):**
1. **Increase max_tokens to 8192** — If thinking consumes ~2000 tokens, 4096 leaves only ~2000 for JSON which gets truncated. Doubling max_tokens gives room for both. The exp 005 note says "truncated (unterminated strings)" — this is truncation, not corruption.
2. **Add stop sequences** — Stop on `<think>` token to prevent thinking from starting
3. **Strip thinking prompt** — Check the actual generated prompt string and remove any thinking-related system tokens before passing to generate
4. **Try Qwen3-32B dense model** — Has standard attention (supports KV cache) and may handle thinking toggle better
5. **More aggressive JSON extraction** — Parse JSON from responses that contain mixed prose+JSON, looking for the last valid JSON object
6. **Increase max_tokens + post-process** — Let thinking happen, ensure JSON isn't truncated, extract JSON from the full response

**Executor implemented ideas #1 + #2 (partial):**
- Game-type-aware system prompt with CRITICAL constraints ✓
- Convert fallback uses available[0] instead of ACTION1 ✓
- Simplified explore prompt JSON format ✓
- **NOT fixed: convert direct mapping still ignores available_actions** — Bug 1 from idea #2.

**CRITICAL FINDING FROM EXP 001 LOG**: "All explore responses failed JSON parse — model outputs prose instead of JSON. Every action falls back to ACTION1."

This means the ROOT CAUSE of 100% Move Up is NOT the game-type awareness or convert bugs — it's that **Qwen 3.5 in thinking mode outputs prose instead of JSON**. The full failure chain:
1. LLM outputs prose (thinking mode leaks or model ignores JSON instruction)
2. `extract_json_from_response` fails to find JSON
3. Explore fallback produces `{"action": "Move Up"}` (hardcoded)
4. Convert direct mapping catches "Move Up" → ACTION1
5. Every single action becomes ACTION1

**Implications for queue priority:**
- Executor's explore prompt changes (removing code fences, "ONLY JSON") might fix this
- If still broken: idea #27 (disable thinking mode for JSON calls) becomes URGENT
- Game-type awareness (#1) and convert fixes (#2) only matter AFTER JSON parsing works
- The explore fallback itself (`{"action": "Move Up"}`) should also be game-type-aware

## Dead Ends

(patterns that don't work)
