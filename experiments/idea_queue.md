# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

---

### 1. [Prompt Engineering] Eliminate separate convert LLM call by outputting ACTION names directly
- **Hypothesis**: The current agent makes TWO LLM calls per explore step — one to decide the action (explore) and one to convert the human-readable action to an ACTION name (convert). Removing the convert call halves LLM inference time per action, making the agent ~2x faster.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In explore.prompt, change the available actions section to list both ACTION names and descriptions (e.g., "ACTION1 = Move Up"). Change the JSON format to require `"action": "ACTION1"` directly. In agent.py `_explore_step`, after parsing the response, check if `result["action"]` starts with "ACTION" and skip the convert call. Fall back to convert only if it doesn't.
- **Expected impact**: ~2x faster per explore step (halves LLM calls). No change in reasoning quality since the model just outputs a different string.

### 2. [Exploration Strategy] Probe clicking actions for ft09/vc33 games
- **Hypothesis**: The current probe phase only tests ACTION1-5 (movement + perform). Games ft09 and vc33 require ACTION6 (clicking), which is never probed. The agent enters explore phase with no knowledge of what clicking does, wasting early explore actions figuring this out.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_probe_step`, after probing ACTION1-5, if ACTION6 is in available_actions, also probe a few click positions (e.g., center of grid, corners). Add 3-5 click probes targeting visible non-background cells detected from the grid data. Record click effects in action_effects.
- **Expected impact**: ft09 and vc33 scores should improve since the agent enters explore phase already knowing what clicking does.

### 3. [State Tracking] Enhanced frame change description with color and position details
- **Hypothesis**: `_describe_frame_change` only reports "N cells changed (X% of grid)" which tells the LLM almost nothing about WHAT changed. Adding details about which colors changed and where helps the LLM reason about game mechanics.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_describe_frame_change`, also report: (a) which colors appeared/disappeared (e.g., "color 3 appeared, color 5 disappeared"), (b) approximate region of change (top/bottom/left/right), (c) whether the change looks like a shift/translation. Keep the description under 100 words.
- **Expected impact**: Better hypotheses from the LLM since it understands what actually changed, leading to fewer wasted actions.

### 4. [Prompt Engineering] Add game-type-aware system prompt
- **Hypothesis**: The system prompt is generic. Adding game-specific strategy hints (ls20 = explore with movement, ft09 = click to toggle colors, vc33 = click-only reasoning) helps the LLM adopt the right strategy faster.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/system.prompt`, `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In agent.py, detect the game type from `context.game.game_id` and pass it to the prompt renderer. In system.prompt, add a conditional section: if game is ls20, add "This is a navigation game. Move to explore hidden state." If ft09, add "This is a pattern puzzle. Click grid cells to change colors, then perform to submit." If vc33, add "This is a click-only visual reasoning game. Only clicking is available."
- **Expected impact**: Faster convergence to correct strategy, especially for ft09/vc33 which are fundamentally different from ls20.

### 5. [Memory Management] Structured memory with separate sections for facts, hypotheses, and action log
- **Hypothesis**: The current memory is an unstructured list of observations. Separating "confirmed facts" from "tentative hypotheses" from "recent actions" helps the LLM distinguish what it knows vs. what it's guessing, leading to better decisions.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: In agent.py, change `context.datastore["memory"]` from a flat string to a dict with keys: `{"facts": [], "hypotheses": [], "recent_actions": []}`. In explore.prompt, render these sections separately with headers. When the LLM returns a confirmed observation, add to facts. Hypotheses get updated/replaced. Recent actions is a sliding window of last 10 actions with effects.
- **Expected impact**: Better reasoning quality, fewer repeated actions, more efficient hypothesis testing.

### 6. [Action Sequencing] Multi-action planning — plan 3 actions at once
- **Hypothesis**: Currently the agent makes one LLM call per action. If the agent plans 3 actions at once and executes them without LLM calls in between, it uses 1/3 the LLM calls while still being systematic.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: In explore.prompt, ask the model to output a `"plan": ["ACTION1", "ACTION2", "ACTION3"]` in addition to the immediate action. In agent.py, store the plan in datastore. On subsequent steps, if a plan exists and the last action didn't cause a significant score change, pop the next action from the plan instead of calling the LLM. Clear the plan if score changes.
- **Expected impact**: ~3x fewer LLM calls during systematic exploration phases. Especially useful for movement-based exploration in ls20.

### 7. [Phase Transitions] Implement actual exploit phase with deterministic action execution
- **Hypothesis**: The agent defines PHASE_EXPLOIT but never enters it. When the agent has high confidence about what to do (e.g., it knows which cells to click in ft09), it should switch to exploit and execute a planned sequence without LLM calls.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_explore_step`, if the LLM returns a `"confidence"` field > 0.8 and a `"plan"` of actions, switch to exploit phase. Add `_exploit_step` method that executes the plan sequentially without LLM calls. If an action doesn't produce expected results, fall back to explore.
- **Expected impact**: When the agent knows the answer, it can execute without LLM latency, saving both time and actions.

### 8. [Exploration Strategy] Systematic grid click scanning for ft09/vc33
- **Hypothesis**: For click-based games, instead of the LLM guessing coordinates, systematically scan visible non-background cells and try clicking them. This is especially useful for ft09 where the agent needs to toggle specific cells.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add a `_click_scan_step` method that identifies non-background cells from the grid data and clicks them systematically (e.g., left-to-right, top-to-bottom). Track which cells have been clicked and their effects. Use this as an alternative exploration strategy when ACTION6 is available and movement actions have no effect.
- **Expected impact**: Much better ft09/vc33 performance by ensuring all clickable cells are discovered.

### 9. [State Tracking] Track score changes per action to identify productive actions
- **Hypothesis**: The agent doesn't explicitly track which actions caused score changes. If it knows "clicking cell (32, 16) increased score by 1", it can repeat successful patterns.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In both `_probe_step` and `_explore_step`, compare `context.game.current_score` with `context.game.previous_score`. When score changes, log the action and coordinates in `context.datastore["score_events"]`. Include this in the explore prompt context.
- **Expected impact**: Agent can identify and repeat successful action patterns, reducing wasted actions.

### 10. [State Tracking] Grid state hashing to detect loops and revisited states
- **Hypothesis**: The agent can waste actions revisiting the same grid state. By hashing grid states and tracking them, the agent can detect loops and take different actions.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add a `_hash_grid` method that creates a compact hash of the current grid. Store seen hashes in `context.datastore["seen_states"]`. In `_explore_step`, if the current state has been seen before, include a warning in the explore prompt: "WARNING: You've seen this state before. Previous actions from this state: [list]. Try something different."
- **Expected impact**: Reduces wasted actions from loops, especially in ls20 navigation.

### 11. [Phase Transitions] Auto re-probe on level transition detection
- **Hypothesis**: When the agent completes a level and enters a new one, the game mechanics might change. Detecting level transitions (score jump or major grid change) and re-entering probe phase ensures the agent maps out the new level's mechanics.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `step()`, before dispatching to phase methods, check if `context.game.current_score > context.game.previous_score` by a significant amount or if the grid changed dramatically (>50% cells different). If so, reset to probe phase and clear action_effects to re-learn mechanics.
- **Expected impact**: Better performance on multi-level games (ft09 has multiple levels) by not assuming old mechanics still apply.

### 12. [Preprocessing] Object detection via connected components analysis
- **Hypothesis**: The LLM receives raw grids but may struggle to identify distinct objects. Preprocessing the grid to find connected components by color and reporting them ("3x2 red block at position (5,3), 1x1 blue cell at (10,8)") gives the LLM structured object information.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add a `_detect_objects` method that runs a BFS/flood-fill to find connected components of same-color cells. Return a list of objects with color, bounding box, and position. Include this object list in the explore prompt context.
- **Expected impact**: Better spatial reasoning by the LLM, especially for click-based games where knowing object positions matters.

### 13. [Memory Management] Score-aware memory that prioritizes productive observations
- **Hypothesis**: Not all observations are equally useful. Observations from actions that changed the score are much more valuable than "nothing happened" observations. Prioritizing these in memory helps the LLM focus on what matters.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: When building memory, tag observations with whether they led to a score change. When memory exceeds the limit, drop "no change" observations first, keeping score-relevant ones. Add a "Productive Actions" section in the explore prompt that only shows score-changing actions.
- **Expected impact**: Better memory utilization, more focused reasoning on what actually works.

### 14. [Exploration Strategy] Double-action probing to detect compound effects
- **Hypothesis**: Some actions may have compound effects (e.g., moving right twice reaches a new area that one move doesn't). Testing each action twice during probe reveals these compound effects.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: In `_probe_step`, after the initial single-action probe, add a second pass that repeats each action that produced a change. Record whether the second application produces the same, different, or no change. This tells us about boundaries and accumulating effects.
- **Expected impact**: Better understanding of game mechanics, especially for ls20 navigation where multiple moves may be needed.

### 15. [Prompt Engineering] Add reasoning steps before action selection in explore prompt
- **Hypothesis**: The current explore prompt asks for observation, analysis, hypothesis, and action all at once. Adding explicit intermediate reasoning steps (identify objects → describe changes → update hypothesis → consider options → choose) may improve reasoning quality with the local Qwen model.
- **Files to modify**: `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Restructure the JSON format to include: `"objects_identified"`, `"changes_from_last_action"`, `"hypothesis_update"`, `"options_considered"`, `"chosen_action"`, `"reasoning"`. This forces the model through a chain-of-thought before committing to an action.
- **Expected impact**: Better reasoning quality from the local model, which benefits from explicit step-by-step decomposition.

### 16. [Memory Management] Cross-level knowledge transfer
- **Hypothesis**: When the agent completes a level and starts a new one, it loses all accumulated knowledge. Carrying forward key facts (like "clicking toggles colors" or "movement shifts the grid") saves actions on subsequent levels.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: On level transition (detected by score jump), save the current `action_effects` and confirmed hypotheses to a `level_knowledge` list in the datastore. On the new level, include a "Previous level knowledge" section in the explore prompt to give the LLM a head start.
- **Expected impact**: Especially valuable for ft09 which has multiple similar levels. Agent can skip re-discovery of basic mechanics.

### 17. [Preprocessing] Grid symmetry detection as a reasoning hint
- **Hypothesis**: Many ARC puzzles involve symmetrical patterns. Detecting horizontal/vertical/rotational symmetry in the grid and telling the LLM about it helps it reason about the puzzle structure.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Add a `_detect_symmetry` method that checks for horizontal mirror, vertical mirror, and 90° rotational symmetry in the grid. Report findings in the explore prompt context (e.g., "Grid has horizontal symmetry" or "No symmetry detected").
- **Expected impact**: Helps the LLM reason about grid structure, potentially useful for ft09 and vc33 pattern puzzles.

### 18. [Action Sequencing] Action macros for common exploration patterns
- **Hypothesis**: Common exploration patterns (e.g., "try all 4 directions", "click each cell in a row") can be pre-defined as macros and executed without individual LLM calls, saving inference time.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Define macros like `SCAN_DIRECTIONS = ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]` and `SCAN_ROW = [click(x,y) for x in range(0, 128, 8)]`. Add a `_execute_macro` method that queues these actions. Let the explore prompt suggest macros by name instead of individual actions.
- **Expected impact**: Faster systematic exploration with fewer LLM calls.

### 19. [Phase Transitions] Stuck detection with random exploration fallback
- **Hypothesis**: When the agent takes N actions without any score change, it's likely stuck. Switching to random exploration can break out of local optima and discover new game mechanics.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`
- **Changes**: Track `actions_since_score_change` in the datastore. If this exceeds a threshold (e.g., 10), switch to a random exploration mode that tries random available actions for 3-5 steps, then returns to explore phase. This costs a few actions but can break deadlocks.
- **Expected impact**: Prevents wasting all remaining actions on a stuck strategy. Especially useful when the LLM's hypothesis is wrong.

### 20. [Preprocessing] Grid differencing visualization in text format
- **Hypothesis**: Instead of just counting changed cells, showing the LLM a text "diff" of the grid (marking which cells changed and what their old/new values were) gives much better spatial reasoning input.
- **Files to modify**: `src/arcagi3/explorer_agent/agent.py`, `src/arcagi3/explorer_agent/prompts/explore.prompt`
- **Changes**: Add a `_grid_diff` method that produces a compact text representation showing only changed cells with their old→new values and (row, col) positions. Include this diff in the explore prompt after the current frame.
- **Expected impact**: Much better understanding of action effects, leading to faster hypothesis formation. Low cost since it's just a few lines of text.

---

## Completed

(none yet)
