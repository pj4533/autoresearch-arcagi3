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

### 3. [Exploration Strategy] Probe clicking actions for ft09/vc33 games
- **Hypothesis**: The current probe phase only tests ACTION1-5. Games ft09 and vc33 require ACTION6 (clicking), which is never probed. The agent enters explore phase with zero knowledge of what clicking does.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_probe_step`, after probing ACTION1-5, if ACTION6 is in available_actions, scan the grid for non-background cells (color != most common color) and click 3-5 of them. Record click effects in action_effects. For VC33 where only ACTION6 is available, the entire probe should be click-based.
- **Expected impact**: ft09 and vc33 enter explore phase knowing what clicking does.

### 4. [Prompt Engineering] Eliminate separate convert LLM call by outputting ACTION names directly
- **Hypothesis**: The agent makes TWO LLM calls per explore step. Removing the convert call halves LLM inference time per action (~2x faster). Also reduces parse failures that trigger the broken ACTION1 fallback.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In explore.prompt, list actions as "ACTION1 = Move Up", "ACTION6 = Click (x,y)". Require JSON output with `"action": "ACTION6", "x": 32, "y": 16`. In agent.py, check if result["action"] starts with "ACTION" and skip convert. Fall back to convert only if needed.
- **Expected impact**: ~2x faster, fewer parse errors, more reliable action selection.

### 5. [State Tracking] Build explicit state graph with loop detection
- **Hypothesis**: LS20 agent repeats Move Down 68% of the time, stuck in loops. A state graph (hash grid → track seen states → warn about revisits) would break this pattern. Competition winners used this approach.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Hash grid state each step. Store in `context.datastore["seen_states"]` dict mapping hash → {actions_tried, visit_count}. In explore prompt, if state seen before: "WARNING: You've visited this state N times. Actions already tried: [list]. You MUST try something different." Track untested actions per state.
- **Expected impact**: Break LS20 loops. State graph was used by 2nd/3rd place competition winners.

### 6. [State Tracking] Enhanced frame change description with color and position details
- **Hypothesis**: `_describe_frame_change` only reports "N cells changed (X% of grid)". The LLM needs to know WHAT changed to form hypotheses. In LS20 traces, the model kept saying "agent is in the 5-colored region" but couldn't tell what was different.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_describe_frame_change`, report: (a) which colors changed (old→new), (b) region of changes (top/bottom/left/right quadrant), (c) direction of shift if applicable. Keep under 100 words.
- **Expected impact**: Better hypotheses, especially for LS20 navigation.

### 7. [Preprocessing] Click target filtering — identify clickable objects
- **Hypothesis**: For click games, the LLM needs to know WHERE to click. Currently it guesses coordinates. Scanning the grid for non-background objects and listing them as click targets transforms a 4096-cell search into a ~10-50 target problem.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add `_find_clickable_targets` that finds non-background cells, groups adjacent same-color cells into objects, returns list with center coordinates. Include in explore prompt: "Clickable targets: red block at (32,16), blue cell at (48,24)."
- **Expected impact**: Dramatically better ft09/vc33 click accuracy.

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

---

## Completed

(none yet)
