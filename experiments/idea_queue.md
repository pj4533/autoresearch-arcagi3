# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

---

### 1. [Prompt Engineering] Eliminate separate convert LLM call by outputting ACTION names directly
- **Hypothesis**: The current agent makes TWO LLM calls per explore step — one to decide the action (explore) and one to convert the human-readable action to an ACTION name (convert). Removing the convert call halves LLM inference time per action, making the agent ~2x faster.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In explore.prompt, change the available actions section to list both ACTION names and descriptions (e.g., "ACTION1 = Move Up"). Change the JSON format to require `"action": "ACTION1"` directly. In agent.py `_explore_step`, after parsing the response, check if `result["action"]` starts with "ACTION" and skip the convert call. Fall back to convert only if it doesn't.
- **Expected impact**: ~2x faster per explore step (halves LLM calls). No change in reasoning quality since the model just outputs a different string.

### 2. [State Tracking] Build explicit state graph with loop detection and frontier tracking
- **Hypothesis**: The 2nd and 3rd place ARC-AGI-3 preview winners used directed state graphs. Nodes = unique grid states (hashed), edges = actions. This gives loop detection (never revisit states), shortest-path replay (navigate back to frontiers), and untested-action tracking. This is the single highest-impact architectural change based on competition results.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add a `StateGraph` class (or methods) in agent.py. On each step: (1) hash the current grid state, (2) check if seen before, (3) record the edge (prev_state, action) → new_state, (4) track which actions have NOT been tried from the current state. In explore prompt, include: "Untested actions from this state: [list]" and "WARNING: state already visited" when applicable. When all actions from current state are tested, pick the action that leads to the least-explored neighbor.
- **Expected impact**: Major reduction in wasted actions from loops. Directly addresses the #1 reason LLM agents score poorly (39% step reduction seen in StateAct research).

### 3. [Exploration Strategy] Probe clicking actions for ft09/vc33 games
- **Hypothesis**: The current probe phase only tests ACTION1-5 (movement + perform). Games ft09 and vc33 require ACTION6 (clicking), which is never probed. The agent enters explore phase with no knowledge of what clicking does, wasting early explore actions figuring this out.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_probe_step`, after probing ACTION1-5, if ACTION6 is in available_actions, also probe a few click positions. Scan the grid for non-background cells and click 3-5 of them (e.g., the largest connected components). Record click effects in action_effects.
- **Expected impact**: ft09 and vc33 scores should improve since the agent enters explore phase already knowing what clicking does.

### 4. [State Tracking] Enhanced frame change description with color and position details
- **Hypothesis**: `_describe_frame_change` only reports "N cells changed (X% of grid)" which tells the LLM almost nothing about WHAT changed. Adding details about which colors changed and where helps the LLM reason about game mechanics.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_describe_frame_change`, also report: (a) which colors appeared/disappeared (e.g., "color 3 appeared, color 5 disappeared"), (b) approximate region of change (top/bottom/left/right), (c) whether the change looks like a shift/translation. Keep the description under 100 words.
- **Expected impact**: Better hypotheses from the LLM since it understands what actually changed, leading to fewer wasted actions.

### 5. [Prompt Engineering] StateAct-style structured state tracking in explore prompt
- **Hypothesis**: Research shows that "chain-of-states" prompting (requiring explicit state tracking at each step) reduced average steps from 31.49 to 19.11 — a 39% reduction. Instead of free-form reasoning, force the model to output structured state at every step.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Restructure the JSON output format to require: `"current_state_summary"` (what the grid looks like now), `"changes_since_last_action"` (what changed), `"mechanics_discovered"` (confirmed rules), `"goal_hypothesis"` (what we think the objective is), `"untested_approaches"` (what haven't we tried), `"action"` (chosen action), `"expected_outcome"` (what we predict will happen). This grounds each decision in explicit state awareness.
- **Expected impact**: ~30-40% reduction in wasted actions based on StateAct research results. Especially effective for preventing goal drift in long action sequences.

### 6. [Prompt Engineering] Add game-type-aware system prompt
- **Hypothesis**: The system prompt is generic. Adding game-specific strategy hints helps the LLM adopt the right strategy faster.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/system.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In agent.py, detect the game type from `context.game.game_id` and pass it to the prompt renderer. In system.prompt, add a conditional section: if game is ls20, add "This is a navigation game. Move to explore hidden state." If ft09, add "This is a pattern puzzle. Click grid cells to change colors, then perform to submit." If vc33, add "This is a click-only visual reasoning game. Only clicking is available."
- **Expected impact**: Faster convergence to correct strategy, especially for ft09/vc33.

### 7. [Preprocessing] Click target filtering — only click non-background objects
- **Hypothesis**: The 64x64 click space has 4096 possible positions, but most are background/empty. The 1st place winner's key insight was filtering no-op actions before executing. Programmatically identifying clickable objects and presenting only those coordinates to the LLM massively reduces the effective action space.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add a `_find_clickable_targets` method that scans the grid for non-background cells (color != 0 or most common color). Group adjacent same-color cells into objects. Return a list of click targets with center coordinates and descriptions. In explore prompt, replace generic "Click object" with a list of specific clickable targets: "Click red block at (32, 16)", "Click blue cell at (48, 24)".
- **Expected impact**: Transforms click games from a 4096-cell search to a ~10-50 target selection problem. Should dramatically improve ft09/vc33 scores.

### 8. [Memory Management] Structured memory with separate sections for facts, hypotheses, and action log
- **Hypothesis**: The current memory is an unstructured list of observations. Separating "confirmed facts" from "tentative hypotheses" from "recent actions" helps the LLM distinguish what it knows vs. what it's guessing, leading to better decisions.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: In agent.py, change `context.datastore["memory"]` from a flat string to a dict with keys: `{"facts": [], "hypotheses": [], "recent_actions": []}`. In explore.prompt, render these sections separately with headers. When the LLM returns a confirmed observation, add to facts. Hypotheses get updated/replaced. Recent actions is a sliding window of last 10 actions with effects.
- **Expected impact**: Better reasoning quality, fewer repeated actions, more efficient hypothesis testing.

### 9. [Action Sequencing] Multi-action planning — plan 3 actions at once
- **Hypothesis**: Currently the agent makes one LLM call per action. If the agent plans 3 actions at once and executes them without LLM calls in between, it uses 1/3 the LLM calls while still being systematic.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: In explore.prompt, ask the model to output a `"plan": ["ACTION1", "ACTION2", "ACTION3"]` in addition to the immediate action. In agent.py, store the plan in datastore. On subsequent steps, if a plan exists and the last action didn't cause a significant score change, pop the next action from the plan instead of calling the LLM. Clear the plan if score changes.
- **Expected impact**: ~3x fewer LLM calls during systematic exploration phases.

### 10. [Phase Transitions] Implement actual exploit phase with deterministic action execution
- **Hypothesis**: The agent defines PHASE_EXPLOIT but never enters it. When the agent has high confidence about what to do, it should switch to exploit and execute a planned sequence without LLM calls.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_explore_step`, if the LLM returns a `"confidence"` field > 0.8 and a `"plan"` of actions, switch to exploit phase. Add `_exploit_step` method that executes the plan sequentially without LLM calls. If an action doesn't produce expected results, fall back to explore.
- **Expected impact**: When the agent knows the answer, it can execute without LLM latency.

### 11. [Prompt Engineering] ReflAct-style goal reflection prompt
- **Hypothesis**: ReflAct research showed 21-28% improvement by grounding decisions in "What is my current state relative to my goal?" rather than "What should I do next?". This prevents goal drift in long action sequences.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Add a reflection section to the explore prompt: "Before choosing an action, reflect: (1) What do I believe the goal is? (2) How close am I to achieving it? (3) What is the most efficient next step toward the goal?" Add a `"goal_reflection"` field to the JSON output.
- **Expected impact**: 20-28% improvement in action efficiency based on ReflAct research.

### 12. [Exploration Strategy] Systematic grid click scanning for ft09/vc33
- **Hypothesis**: For click-based games, instead of the LLM guessing coordinates, systematically scan visible non-background cells and try clicking them.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add a `_click_scan_step` method that identifies non-background cells from the grid data and clicks them systematically. Track which cells have been clicked and their effects. Use this as an alternative exploration strategy when ACTION6 is available and movement actions have no effect.
- **Expected impact**: Much better ft09/vc33 performance by ensuring all clickable cells are discovered.

### 13. [State Tracking] Track score changes per action to identify productive actions
- **Hypothesis**: The agent doesn't explicitly track which actions caused score changes. If it knows "clicking cell (32, 16) increased score by 1", it can repeat successful patterns.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In both `_probe_step` and `_explore_step`, compare `context.game.current_score` with `context.game.previous_score`. When score changes, log the action and coordinates in `context.datastore["score_events"]`. Include this in the explore prompt context.
- **Expected impact**: Agent can identify and repeat successful action patterns.

### 14. [Phase Transitions] Auto re-probe on level transition detection
- **Hypothesis**: When the agent completes a level and enters a new one, re-entering probe phase ensures the agent maps out the new level's mechanics.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `step()`, detect level transitions via score jumps or dramatic grid changes (>50% cells different). If detected, reset to probe phase and clear action_effects to re-learn mechanics.
- **Expected impact**: Better multi-level performance (ft09 has multiple levels).

### 15. [Memory Management] Cross-level knowledge transfer
- **Hypothesis**: When moving to a new level, all accumulated knowledge is lost. Carrying forward key mechanics saves actions on subsequent levels.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: On level transition, save current `action_effects` and confirmed hypotheses to `level_knowledge` list. On new level, include "Previous level knowledge" in explore prompt.
- **Expected impact**: Especially valuable for ft09 which has multiple similar levels.

### 16. [Preprocessing] Object detection via connected components analysis
- **Hypothesis**: Preprocessing the grid to find connected components and reporting them gives the LLM structured object information.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add a `_detect_objects` method using BFS/flood-fill to find connected components. Return objects with color, bounding box, and center position. Include in explore prompt.
- **Expected impact**: Better spatial reasoning, especially for click-based games.

### 17. [Phase Transitions] Stuck detection with random exploration fallback
- **Hypothesis**: When the agent takes N actions without score change, random exploration can break deadlocks.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Track `actions_since_score_change` in datastore. If exceeds threshold (e.g., 10), try random actions for 3-5 steps. Return to explore after.
- **Expected impact**: Prevents wasting all actions on a stuck strategy.

### 18. [Memory Management] Score-aware memory prioritizing productive observations
- **Hypothesis**: Observations from score-changing actions are much more valuable. Prioritizing these in memory helps the LLM focus on what matters.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Tag observations with score-change status. When memory exceeds limit, drop "no change" observations first.
- **Expected impact**: Better memory utilization.

### 19. [Preprocessing] Grid differencing visualization in text format
- **Hypothesis**: Showing the LLM a text diff of the grid gives much better spatial reasoning input than just cell counts.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Add `_grid_diff` method producing compact text showing changed cells with old→new values and positions.
- **Expected impact**: Better understanding of action effects.

### 20. [Exploration Strategy] Double-action probing to detect compound effects
- **Hypothesis**: Some actions have compound effects (moving right twice reaches new areas). Testing each action twice reveals this.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_probe_step`, after initial single-action probe, repeat actions that produced changes and record compound effects.
- **Expected impact**: Better understanding of ls20 navigation mechanics.

### 21. [Action Sequencing] Action macros for common exploration patterns
- **Hypothesis**: Pre-defined exploration sequences can be executed without individual LLM calls.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Define macros like `SCAN_DIRECTIONS` and `SCAN_ROW`. Add `_execute_macro` method. Let explore prompt suggest macros by name.
- **Expected impact**: Faster systematic exploration with fewer LLM calls.

### 22. [Preprocessing] Grid symmetry detection as a reasoning hint
- **Hypothesis**: Detecting symmetry helps the LLM reason about puzzle structure.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add `_detect_symmetry` method checking horizontal/vertical/rotational symmetry. Report in explore prompt.
- **Expected impact**: Potentially useful for ft09/vc33 pattern puzzles.

### 23. [Prompt Engineering] Adopt ADCR's `---` divider for combined analysis + memory update
- **Hypothesis**: ADCR gets analysis AND memory update in one LLM call by using a `---` separator. The model writes analysis above the divider and the updated memory scratchpad below. This is proven to work in the reference agent and saves prompt/response overhead.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In explore.prompt, add instruction: "After your JSON response, write `---` then update your memory scratchpad with key observations and hypotheses." In agent.py `_explore_step`, after getting response text, split on `---`. Parse JSON from the first part. Use the second part as the new memory value. This replaces the current approach of extracting memory from within the JSON.
- **Expected impact**: Cleaner memory management, model has explicit space for structured note-taking. Proven pattern from ADCR.

### 24. [Prompt Engineering] Score change feedback — tell model when actions succeed
- **Hypothesis**: ADCR detects score increases and tells the model "NEW LEVEL!!!! Whatever you did must have been good!" Explorer provides no feedback when score changes. Positive reinforcement helps the model learn what works and repeat successful patterns.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: In `_explore_step`, check if `context.game.current_score > context.game.previous_score`. If so, prepend to the explore prompt: "SCORE INCREASED! Your previous action was effective. Score: {old} → {new}." Also detect score decreases: "SCORE DECREASED — your last action was harmful."
- **Expected impact**: Faster learning from feedback. Agent can identify and repeat successful strategies.

### 25. [Memory Management] Multi-turn conversation context from previous step
- **Hypothesis**: ADCR includes the previous prompt and model response as conversation history, giving the model continuity between steps. Explorer sends fresh single-message prompts each time. Adding conversation context should reduce repeated reasoning and help the model build on its previous analysis.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_explore_step`, store the previous explore prompt and response in `context.datastore["previous_prompt"]` and `context.datastore["previous_response"]`. When building messages for the next step, include them as a user/assistant message pair before the current prompt. This gives the model 1 turn of conversation history.
- **Expected impact**: Better continuity between steps, less redundant reasoning, model can reference its own previous analysis.

### 26. [Preprocessing] Use image_diff() for visual change highlighting between frames
- **Hypothesis**: The `image_diff()` utility already exists in the codebase but Explorer doesn't use it. ADCR sends a diff-highlighted image showing what changed between frames. This gives the LLM a clear visual signal of what changed, much better than just counting cells.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_explore_step`, when vision is enabled and there's a previous frame image, compute `diff_img = image_diff(prev_img, curr_img)`. Add it to the message content after the current frame images. Label it: "Diff image (changed pixels highlighted in red)."
- **Expected impact**: Much better visual understanding of action effects. Low effort since the utility already exists. Only applies when vision is enabled.

---

## Completed

(none yet)
