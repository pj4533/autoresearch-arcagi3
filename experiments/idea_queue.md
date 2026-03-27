# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PRIORITY REORDER (2026-03-27): Based on analysis of 95+ prior experiments, ALL scoring 0. See research notes for diagnostic details.**

---

### 1. [Prompt Engineering] Add game-type-aware system prompt with FORCEFUL action constraints
- **Hypothesis**: VC33 is click-only but the agent sends 100% movement actions. FT09 requires clicking but agent uses 84% Move Down. The available actions list in the explore prompt is being ignored. We need to FORCEFULLY tell the model which actions to use per game type.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/system.prompt`, `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In agent.py, detect game type from `context.game.game_id` and pass to prompt. In system.prompt, add conditional: if vc33, "THIS IS A CLICK-ONLY GAME. You MUST use Click actions with x,y coordinates. Movement actions DO NOT WORK." If ft09, "This is a pattern puzzle. You MUST click grid cells to change colors, then Perform to submit." If ls20, "This is a navigation game. Use movement actions." In explore.prompt, add "CRITICAL: You MUST choose from the available actions listed below. Other actions will be REJECTED." Repeat the constraint.
- **Expected impact**: Should fix VC33 (currently 100% wasted actions) and FT09 (84% wrong actions). This is the single most impactful change possible.

### 2. [Exploration Strategy] Fix convert fallback to use valid action from available_actions
- **Hypothesis**: When the LLM outputs an unparseable action, `_convert_to_game_action` falls back to `{"action": "ACTION1"}` — which is Move Up. For VC33 (click-only), this fallback sends an invalid action. The fallback should use the FIRST available action, not hardcoded ACTION1.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_convert_to_game_action`, change the final fallback from `return {"action": "ACTION1"}` to: `available = self._get_available_action_names(context); return {"action": available[0] if available else "ACTION1"}`. For VC33 where only ACTION6 is available, this falls back to clicking instead of movement.
- **Expected impact**: Prevents catastrophic fallback behavior. Even failed parses will at least try valid actions.

### 3. [Exploration Strategy] Programmatic click probe with object detection (NO LLM needed)
- **Hypothesis**: For click-only games like VC33, the probe phase should skip the LLM entirely and programmatically scan the grid for clickable objects. VC33 level 1 only needs 6 clicks to solve — a smart scan could solve it in the probe phase alone. Even for FT09, clicking non-background objects reveals mechanics faster than asking the LLM to guess coordinates.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Rewrite `_probe_step` for click games:
  1. **Find background color**: Count color frequencies in grid. Most common = background (usually 0 or 3).
  2. **Find non-background objects**: BFS/flood-fill to find connected components of non-background cells. For each, record: color, bounding box, center (row, col), cell count.
  3. **Convert grid coords to click coords**: Multiply by 2 (grid is 64x64, clicks are 0-127).
  4. **Click top-N objects by size**: Click center of each distinct non-background object, largest first. After each click, record frame change via `_describe_frame_change()` and score change.
  5. **Store results**: Save click targets list and effects in `context.datastore["click_targets"]` and `action_effects`.
  6. For VC33 (ACTION6 only): Skip ALL movement probing, go straight to click scan.
  7. For FT09 (ACTION5+ACTION6): After click scan, also try Perform to test submission.
- **Expected impact**: VC33 could score in the PROBE PHASE without any LLM calls. FT09 enters explore with click mechanics fully mapped. This is potentially the highest-impact single change for scoring.

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

### 27. [Prompt Engineering] Disable thinking mode for JSON/convert calls (Qwen-specific)
- **Hypothesis**: Qwen3.5's thinking mode can leak `<think>` tags into JSON output (documented bug). The convert step just needs a simple ACTION mapping — thinking adds wasted tokens and risks JSON corruption. Disabling thinking for convert calls saves tokens and improves JSON reliability.
- **Files to modify**: `src/arcagi3/adapters/mlx_adapter.py` (or wherever MLX provider is configured), `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add ability to pass `enable_thinking=False` to the MLX adapter's chat template for specific calls. Use this for convert calls. Keep thinking enabled for explore calls where reasoning helps. Also lower temperature to 0.1-0.3 for convert calls.
- **Expected impact**: More reliable JSON parsing, fewer fallback-to-ACTION1 failures, reduced token waste.

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

(none yet)
