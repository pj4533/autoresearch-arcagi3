# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**COORDINATE BUG FOUND (2026-03-28): Click coordinate formula is WRONG. Use `click_x = col * 2, click_y = row * 2` NOT `col * 127 / (cols-1)`. The base agent divides by 2 (`x // 2` in agent.py:507), so `col * 2 // 2 = col` gives the correct grid cell. Current formula gives col=31 instead of col=25 for 51x51 grids — every click misses by 6 cells. THIS IS WHY ALL CLICKS SHOW "NO VISIBLE CHANGE". Fix this and clicks will land on actual objects.**

---

### 1. [Prompt Engineering] Add game-type-aware system prompt with FORCEFUL action constraints
- **Hypothesis**: VC33 is click-only but the agent sends 100% movement actions. FT09 requires clicking but agent uses 84% Move Down. The available actions list in the explore prompt is being ignored. We need to FORCEFULLY tell the model which actions to use per game type.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/system.prompt`, `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In agent.py, detect game type from `context.game.game_id` and pass to prompt. In system.prompt, add conditional: if vc33, "THIS IS A CLICK-ONLY GAME. You MUST use Click actions with x,y coordinates. Movement actions DO NOT WORK." If ft09, "This is a pattern puzzle. You MUST click grid cells to change colors, then Perform to submit." If ls20, "This is a navigation game. Use movement actions." In explore.prompt, add "CRITICAL: You MUST choose from the available actions listed below. Other actions will be REJECTED." Repeat the constraint.
- **Expected impact**: Should fix VC33 (currently 100% wasted actions) and FT09 (84% wrong actions). This is the single most impactful change possible.

### 2. [Exploration Strategy] Fix THREE hardcoded "Move Up" fallbacks across agent code
- **Hypothesis**: There are THREE hardcoded "Move Up"/ACTION1 fallbacks in the agent. EXP 001 showed ALL explore responses fail JSON parse → every action hits these fallbacks → 100% Move Up. Even with the game-type prompt fix, if JSON parsing fails, the agent still defaults to Move Up for click-only games.
  - **Bug 1 (EXPLORE parse fallback, line ~253)**: `result = {"action": "Move Up", "reasoning": "Fallback due to parse error"}` — when JSON parse fails (which is EVERY action per exp 001), this hardcodes Move Up.
  - **Bug 2 (CONVERT direct mapping)**: `action_map.get(human_action.lower())` returns ACTION2 for "Move Down" WITHOUT checking available_actions.
  - **Bug 3 (CONVERT final fallback)**: Was `{"action": "ACTION1"}` — executor already fixed to `available[0]`. ✓ DONE.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**:
  1. **Bug 1 (CRITICAL)**: Change explore parse fallback to use available actions: `available = self._get_available_action_names(context); fallback_action = available[0] if available else "ACTION1"`. For ACTION6, add coords: `{"action": "Click (64, 64)", ...}`.
  2. **Bug 2**: After direct mapping, validate: `if direct and direct in self._get_available_action_names(context): return {"action": direct}`.
  3. Bug 3: Already fixed. ✓
- **Expected impact**: When JSON parse fails (which may still happen), the fallback will at least try valid actions for the game type. This is the safety net beneath the game-type prompt.

### 3. [Exploration Strategy] Refine click probe: filter structural objects, prioritize small targets
- **Hypothesis**: Exp 004 showed click probe works mechanically (0.2s/action!) but clicks wrong objects. VC33 detected 10 targets including color=0 (size 848) and color=5 (size 96) — these are structural elements (borders, frames), not interactive game objects. The interactive objects in VC33 are smaller colored blocks (size ~4-64). Need smarter filtering.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes** (refine existing `_detect_objects` and `_click_probe_step`):
  1. **Filter structural colors**: Skip color 0 (white/background) and color 5 (black/borders) in addition to the most-common background color. These are almost always non-interactive.
  2. **Size filtering**: Prioritize objects with size 4-100 cells. Very large objects (>200) are usually backgrounds/frames. Very small (1-2) may be noise.
  3. **Sort by size ascending** (smallest first) instead of descending — small distinctive objects are more likely interactive in VC33.
  4. **Track click effects**: After each click, check if frame changed. If no change after clicking objects of a given color, skip remaining objects of that color.
  5. **Re-detect after score change**: Already implemented ✓. On score increase, re-scan for new level's objects.
  6. **Multiple background colors**: Instead of just the most common color, treat the top 2-3 most common colors as background (they're usually the floor/walls/borders).
- **Expected impact**: With proper filtering, the probe should click actual interactive objects. VC33 level 1 needs ~6 clicks — if even half of filtered targets are correct, it could score.

### 4. [Prompt Engineering] Eliminate separate convert LLM call by outputting ACTION names directly
- **Hypothesis**: The agent makes TWO LLM calls per explore step. Removing the convert call halves LLM inference time per action (~2x faster). Also reduces parse failures that trigger the broken ACTION1 fallback.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In explore.prompt, list actions as "ACTION1 = Move Up", "ACTION6 = Click (x,y)". Require JSON output with `"action": "ACTION6", "x": 32, "y": 16`. In agent.py, check if result["action"] starts with "ACTION" and skip convert. Fall back to convert only if needed.
- **Expected impact**: ~2x faster, fewer parse errors, more reliable action selection.

### 5. [Preprocessing] Click target list in explore prompt (builds on #3's object detection)
- **Hypothesis**: After #3 identifies objects, the explore prompt should list them as named click targets instead of asking the LLM to guess coordinates. "Click target A: 5x3 color-9 block at (64, 32)" is much easier for the model than raw grid analysis. VC33 is the easiest scoring target (6 baseline clicks for level 1) — making the LLM accurate at clicking is the fastest path to a non-zero score.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Reuse the object detection from #3 (or add `_find_clickable_targets` if not yet present). In explore prompt, add a "## Clickable Targets" section listing each non-background object: letter label (A, B, C...), color, size, center coordinates. Change the action format for clicks to reference targets: `"action": "ACTION6", "target": "A"` which maps to that target's coordinates. This eliminates coordinate guessing entirely.
- **Expected impact**: Near-perfect click accuracy for VC33/FT09. Model just picks which target to click, not where. Fastest path to first non-zero score.

### 6. [State Tracking] Build explicit state graph with loop detection (MUST mask status bar)
- **Hypothesis**: LS20 agent repeats Move Down 68% of the time, stuck in loops. A state graph (hash grid → track seen states → warn about revisits) would break this pattern. Competition winners used this approach. **CRITICAL**: The game has a status bar/step counter that changes every step. Without masking it before hashing, every frame looks unique and the graph can't detect revisits.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: (1) Add `_mask_status_bar(grid)` that zeros out the top/bottom few rows (or detect the step counter region by finding the row that changes every frame). (2) Hash the MASKED grid, not the raw grid. (3) Store in `context.datastore["state_graph"]` dict mapping hash → {actions_tried: {action: result_hash}, visit_count}. (4) In explore prompt, if state seen before: "WARNING: Visited N times. Tried: [list]. MUST try something different." (5) When all actions from current state tested, suggest the action leading to least-explored neighbor.
- **Expected impact**: Break LS20 loops. State graph was used by 2nd/3rd place competition winners. Status bar masking is essential — without it, this doesn't work.

### 7. [State Tracking] Enhanced frame change description with color and position details
- **Hypothesis**: `_describe_frame_change` only reports "N cells changed (X% of grid)". The LLM needs to know WHAT changed to form hypotheses. In LS20 traces, the model kept saying "agent is in the 5-colored region" but couldn't tell what was different.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_describe_frame_change`, report: (a) which colors changed (old→new), (b) region of changes (top/bottom/left/right quadrant), (c) direction of shift if applicable. Keep under 100 words.
- **Expected impact**: Better hypotheses, especially for LS20 navigation.

### 8. [Prompt Engineering] StateAct-style structured state tracking in explore prompt
- **Hypothesis**: In traces, the model's observations are repetitive ("grid is 51x51, mostly 3s"). StateAct-style prompting forces explicit state tracking, reducing steps by 39% in research. Requires model to explicitly state what it knows, what it's tried, and what's untested.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Restructure JSON output: `"current_state_summary"`, `"changes_since_last_action"`, `"mechanics_discovered"`, `"goal_hypothesis"`, `"untested_approaches"`, `"action"`, `"expected_outcome"`.
- **Expected impact**: 30-40% reduction in wasted actions.

### 9. [Phase Transitions] Stuck detection with alternative strategy fallback
- **Hypothesis**: All games show the agent repeating the same actions with no progress. After N actions with no score change, the agent should try a radically different strategy (random actions, clicking instead of movement, etc.).
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Track `actions_since_score_change`. If > 8: add "WARNING: No progress in 8 actions. Your current strategy is not working. Try a COMPLETELY DIFFERENT approach." If > 15: force random valid actions for 3 steps.
- **Expected impact**: Break deadlocks that currently consume all 25 actions.

### 10. [Memory Management] Structured memory with separate facts/hypotheses/actions
- **Hypothesis**: Current memory is flat text. Separating confirmed facts from hypotheses helps the LLM avoid repeating failed approaches.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Dict-based memory with `facts`, `hypotheses`, `recent_actions` keys. Render separately in prompt.
- **Expected impact**: Better reasoning quality, fewer repeated actions.

### 11. [Action Sequencing] Multi-action planning — plan 3 actions at once
- **Hypothesis**: One LLM call per action is expensive (~14.5 sec on Qwen MLX). Planning 3 actions cuts LLM calls by 3x.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Ask model to output `"plan": ["ACTION1", "ACTION2", "ACTION3"]`. Execute plan without LLM calls. Clear plan if score changes.
- **Expected impact**: ~3x fewer LLM calls.

### 12. [Phase Transitions] Implement actual exploit phase
- **Hypothesis**: Agent defines PHASE_EXPLOIT but never enters it. When confident, execute planned sequences without LLM calls.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add `_exploit_step`. Enter exploit when LLM returns confidence > 0.8 with a plan. Execute plan steps. Fall back to explore if unexpected result.
- **Expected impact**: Faster execution when agent knows the answer.

### 13. [Prompt Engineering] ReflAct-style goal reflection prompt
- **Hypothesis**: ReflAct showed 21-28% improvement by grounding decisions in goal progress rather than open-ended "what next."
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Add reflection questions: "What is the goal? How close am I? What's the most efficient next step?"
- **Expected impact**: 20-28% improvement in action efficiency.

### 14. [Exploration Strategy] Systematic grid click scanning for ft09/vc33
- **Hypothesis**: For click games, systematically scan non-background cells.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add `_click_scan_step` identifying and clicking non-background cells left-to-right, top-to-bottom.
- **Expected impact**: Better ft09/vc33 discovery.

### 15. [State Tracking] Track score changes per action
- **Hypothesis**: Agent doesn't know which actions caused score changes.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Compare scores before/after each action. Log score events. Include in explore prompt.
- **Expected impact**: Repeat successful patterns.

### 16. [Prompt Engineering] Score change feedback — tell model when actions succeed
- **Hypothesis**: ADCR detects "NEW LEVEL!!!!" on score increase. Explorer gives no feedback.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Prepend "SCORE INCREASED!" or "SCORE DECREASED!" to explore prompt when score changes.
- **Expected impact**: Faster learning from feedback.

### 17. [Phase Transitions] Auto re-probe on level transition
- **Hypothesis**: New levels may have different mechanics. Re-probe on score jumps.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Detect score jumps or >50% grid change. Reset to probe phase.
- **Expected impact**: Better multi-level performance.

### 18. [Memory Management] Cross-level knowledge transfer
- **Hypothesis**: Level transitions lose all knowledge. Carry forward mechanics.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Save action_effects and hypotheses to level_knowledge on transitions.
- **Expected impact**: Skip re-discovery on subsequent levels.

### 19. [Preprocessing] Object detection via connected components
- **Hypothesis**: BFS/flood-fill to find objects gives LLM structured spatial info.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add `_detect_objects` method. Report objects with color, size, position.
- **Expected impact**: Better spatial reasoning for click games.

### 20. [Memory Management] Multi-turn conversation context from previous step
- **Hypothesis**: ADCR includes previous prompt/response as history. Explorer sends fresh messages.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Store previous prompt and response. Include as user/assistant message pair.
- **Expected impact**: Better continuity between steps.

### 21. [Prompt Engineering] Adopt ADCR's `---` divider for combined analysis + memory
- **Hypothesis**: ADCR gets analysis AND memory in one call via `---` separator. Proven pattern.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add "write --- then update memory scratchpad" instruction. Split response on `---`.
- **Expected impact**: Cleaner memory management, proven in ADCR.

### 22. [Preprocessing] Grid differencing visualization in text format
- **Hypothesis**: Text diff showing changed cells with old→new values helps reasoning.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Add `_grid_diff` method. Include diff in prompt.
- **Expected impact**: Better action effect understanding.

### 23. [Preprocessing] Use image_diff() for visual change highlighting
- **Hypothesis**: `image_diff()` utility exists but Explorer doesn't use it. ADCR uses it.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: When vision enabled, compute and include diff image between frames.
- **Expected impact**: Better visual change detection.

### 24. [Exploration Strategy] Double-action probing for compound effects
- **Hypothesis**: Testing each action twice reveals compound effects (e.g., two right moves).
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Second probe pass repeating actions that caused changes.
- **Expected impact**: Better LS20 navigation understanding.

### 25. [Action Sequencing] Action macros for exploration patterns
- **Hypothesis**: Pre-defined sequences executed without individual LLM calls.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Define macros like SCAN_DIRECTIONS. Add `_execute_macro` method.
- **Expected impact**: Faster exploration.

### 26. [Preprocessing] Grid symmetry detection
- **Hypothesis**: Detecting symmetry helps puzzle reasoning.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add `_detect_symmetry` method. Report in prompt.
- **Expected impact**: Potentially useful for ft09/vc33.

### 27. [Prompt Engineering] Fix JSON truncation — increase max_tokens or suppress thinking — URGENT
- **Hypothesis**: `enable_thinking=False` was tried but DID NOT WORK (Qwen3.5 silently ignores it). Completion tokens are still ~3500/action. Exp 005 noted "truncated (unterminated strings)" — the 4096 max_tokens is too low because ~2000 tokens go to thinking, leaving only ~2000 for JSON which gets cut off. The root cause of JSON parse failure is TRUNCATION, not corruption.
- **Files to modify**: `src/arcagi3/adapters/mlx_adapter.py`, `src/arcagi3/models.yml`
- **Changes** (try in order):
  1. **SIMPLEST: Increase max_tokens to 8192** in models.yml for qwen3.5-35b-local config. This gives room for thinking (~2000 tok) + full JSON (~500 tok) with margin. Will be slower per action but JSON should actually complete.
  2. **Strip thinking from prompt**: After `apply_chat_template`, inspect the generated prompt string and remove any `<|im_start|>think` or thinking-instruction tokens before passing to generate.
  3. **Add a stop string**: Pass `stop=["<think>"]` or similar to the generate call to prevent thinking from starting.
  4. **Try Qwen3-32B dense** (`qwen3-32b-local`): Standard attention, may handle thinking differently, supports KV cache.
- **Expected impact**: Option 1 (increase max_tokens) should immediately fix JSON truncation. Slower per action but JSON parse rate should jump from ~8% to 50%+. This unblocks all other improvements.

### 28. [Prompt Engineering] Aggressive prompt compression (Qwen MLX has no KV cache reuse)
- **Hypothesis**: Qwen3.5-35B on MLX has NO KV cache reuse due to hybrid DeltaNet architecture (ml-explore/mlx-lm#980). Every inference recomputes the full prompt from scratch. Compressing the prompt saves real wall-clock time on EVERY step. Currently ~14.5 sec/action.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/system.prompt`, `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: (1) Shorten system prompt to essentials. (2) After first step, abbreviate action descriptions to short codes. (3) Hard character limits on memory/hypothesis (200 chars each). (4) Use compact grid representation (only send non-background regions). (5) Set per-step max_tokens: 512 for explore, 128 for convert.
- **Expected impact**: 20-40% reduction in per-step latency. More actions per time budget.

### 29. [Prompt Engineering] Add explicit uncertainty permission to reduce hallucinated hypotheses
- **Hypothesis**: Qwen3.5 has high hallucination rate and confidently asserts incorrect hypotheses. Adding "If you are uncertain about the game rules, say 'UNCERTAIN' rather than guessing" to the system prompt could reduce false-positive hypotheses that lead to wasted actions on wrong strategies.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/system.prompt`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Add to system prompt: "It's better to say you're uncertain than to guess wrong. Mark hypotheses with confidence: HIGH/MEDIUM/LOW." In explore prompt, add a `"confidence"` field to JSON output. Use confidence to decide whether to test hypothesis or gather more data.
- **Expected impact**: Fewer wasted actions on wrong hypotheses. Better explore/exploit balance.

### 30. [Exploration Strategy] Hypothesis-driven probing — ask LLM "what to test?" not "what to do?"
- **Hypothesis**: Currently the LLM decides actions directly ("Move Down"). Humans explore differently — they form hypotheses ("I think clicking the red object does X") then test them. Reframing the explore prompt to ask for HYPOTHESES rather than ACTIONS, then executing tests programmatically, is closer to how humans solve these puzzles and reduces LLM calls.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Change explore prompt to ask: "What is your current hypothesis about the game rules? What experiment would test this hypothesis? What specific action sequence would confirm or refute it?" Output: `{"hypothesis": "...", "test_action": "ACTION1", "expected_if_true": "...", "expected_if_false": "..."}`. In agent.py, execute the test action, compare result to predictions, and update hypothesis confidence in memory. Only call LLM again when the test result is ambiguous or hypothesis is confirmed/refuted.
- **Expected impact**: Better hypothesis quality, fewer wasted actions, LLM called every 2-3 actions instead of every action.

### 31. [Exploration Strategy] Probe ACTION7 (undo) to enable recovery from bad states
- **Hypothesis**: ACTION7 (undo) is available but never probed or used. LS20 has a three-life mechanic where some actions can kill the agent. Knowing undo works enables bolder exploration since mistakes can be reversed.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_probe_step`, if ACTION7 is in available_actions, test it after another action. Record whether undo successfully reverses the previous action. Store `undo_available: true/false` in datastore. In explore prompt, if undo works: "Undo is available — you can safely try risky actions."
- **Expected impact**: Enables bolder exploration in LS20. Prevents permanent loss from risky actions.

### 32. [Exploration Strategy] For VC33: brute-force click scan as entire strategy (no LLM)
- **Hypothesis**: VC33 level 1 needs only 6 clicks. If we skip the LLM entirely for VC33 and just programmatically click every non-background object, we could solve levels purely through systematic scanning. With 40 max actions and ~20-50 distinct objects on a 64x64 grid, we have enough budget to try them all. This trades LLM "intelligence" for exhaustive coverage — since the agent currently scores 0 with the LLM anyway, this can only be an improvement.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `step()`, if game_id contains "vc33" and phase is not exploit: (1) detect all non-background objects, (2) click them sequentially (largest first), (3) after each click check score, (4) if score increases, re-scan (new level may have different layout). No LLM calls at all for VC33. Essentially replace the entire explore phase with a programmatic scan.
- **Expected impact**: Should solve VC33 level 1 (6 clicks) and possibly level 2 (13 clicks) within 40 actions. Even partial progress = breakthrough since current score is 0.

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
