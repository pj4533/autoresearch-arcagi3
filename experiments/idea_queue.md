# Idea Queue

**ORDER = PRIORITY. Executor tests #1 first, then #2, etc.**

**PHILOSOPHY (2026-03-29, hybrid approach): Claude Code (Opus 4.6) provides reasoning. Stategraph agent runs pure programmatic (LLM_INTERVAL=0). The executor investigates game mechanics via arc CLI, then makes targeted code changes. Focus on vc33 (interactive clicks work, 50 lives per level, 6 baseline clicks for level 1).**

---

### 1. [Puzzle Logic] Investigate vc33 visually — understand what clicks DO
- **Hypothesis**: After 17 stategraph experiments, nobody has visually inspected what happens when clicking vc33 objects. The executor (Claude Code) can view frame images via `arc state --image`. Understanding what clicks DO is the prerequisite for all puzzle-solving strategies. vc33 is "volume/height adjustment" — we need to see what heights look like and what the goal state is.
- **Files to modify**: None initially — this is investigation. Then agent.py based on findings.
- **Changes**: Use arc CLI to investigate:
  ```bash
  arc start vc33 --max-actions 50
  arc state --image                    # See initial grid
  # Click the interactive objects (color 9 produces 265 cell changes)
  # Try several different objects and observe effects
  arc state --image                    # See what changed
  arc end
  ```
  Then implement a puzzle-solving heuristic based on what you observe. For example, if clicking adjusts height of a bar toward a target line, implement "click objects whose height doesn't match the target."
- **Expected impact**: Understanding the puzzle is the prerequisite for solving it. Every previous experiment failed because the agent didn't understand the game.

### 2. [Life Management] Track remaining lives from health bar
- **Hypothesis**: vc33's health bar is in row 0: orange (color 7) = remaining, yellow (color 4) = depleted. The agent can parse this to know how many lives remain. When lives are low (< 10), the agent should stop exploratory clicks and only try confirmed-productive actions.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. Add `_parse_health_bar(grid)` method: count color 7 cells in row 0, compute remaining = count / 64 * max_lives (50 for level 1)
  2. Store remaining lives in `context.datastore["lives"]`
  3. When lives < 10: switch to conservative mode — only click objects that previously produced frame changes without reducing lives
  4. When lives < 3: stop clicking entirely (preserve remaining for known-good actions)
- **Expected impact**: Prevents GAME_OVER from wasted exploration clicks. Preserves lives for the winning sequence.

### 3. [Click Target Detection] Track productive vs destructive click effects
- **Hypothesis**: Not all clicks are equal. Some produce large frame changes (interactive), some produce no change (decorative), some might reduce lives faster (dangerous). By categorizing click effects, the agent can prioritize productive clicks and avoid destructive ones.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. After each click, record: `{position, color, size, cells_changed, health_before, health_after}`
  2. Categorize: "productive" (cells_changed > 10 AND no extra health loss), "neutral" (no change), "dangerous" (extra health loss beyond the base 1-per-click cost)
  3. In `_try_click()`, prioritize "productive" positions in new states, skip "dangerous" ones
  4. Track by object COLOR (since same-color objects likely have similar effects)
- **Expected impact**: Focuses remaining lives on the most promising click targets.

### 4. [Puzzle Logic] Click effect direction analysis — what changes WHERE
- **Hypothesis**: When clicking a vc33 interactive object (265 cells changed), the agent currently only knows "265 cells changed." It doesn't know WHAT changed or WHERE. Analyzing the change direction (which cells changed from what to what, in which region) reveals the puzzle mechanic. For "volume/height adjustment," clicking might move a bar up/down — the direction tells us if we're getting closer to the goal.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`, `src/arcagi3/utils/formatting.py`
- **Changes**:
  1. After each productive click, compute detailed diff: which rows/cols changed, predominant color transitions, direction of change (up/down/left/right shift)
  2. Store as `{click_position, change_region, change_direction, color_transitions}` in `context.datastore["click_effects"]`
  3. Use this to decide: "clicking object A moves things LEFT, clicking object B moves things RIGHT." Then plan clicks based on where things need to go.
- **Expected impact**: Enables goal-directed clicking instead of random exploration.

### 5. [Frame Analysis] Goal state detection — identify what the target looks like
- **Hypothesis**: vc33 levels likely have a visible "target" or "goal" state shown somewhere on the grid (e.g., a reference pattern to match). Detecting this gives the agent a concrete objective. The agent can then compare current state to goal and click to reduce the difference.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`, `src/arcagi3/utils/formatting.py`
- **Changes**:
  1. At game start, analyze grid for symmetry or dual-panel layout (many puzzle games show current state on one side and goal on the other)
  2. Look for: mirrored regions, separated panels, reference indicators
  3. If found: compute difference between current state and goal state
  4. Click strategy: click objects that reduce the difference
- **Expected impact**: Goal-directed behavior instead of blind exploration.

### 6. [Action Priority] GAME_OVER avoidance — don't repeat fatal sequences
- **Hypothesis**: When the agent reaches GAME_OVER, it should record the action sequence that led there. On subsequent games or levels, avoid action sequences that previously caused death.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**:
  1. When GAME_OVER occurs, save the last N actions (the "fatal sequence") to `context.datastore["fatal_sequences"]`
  2. Before choosing an action, check if it would continue a known fatal sequence
  3. If so, choose a different action
  4. This is cross-game learning: fatal sequences persist in the datastore
- **Expected impact**: Avoids repeating known-bad action patterns.

### 7. [State Graph Navigation] vc33 click-only mode — eliminate movement waste
- **Hypothesis**: vc33 only supports ACTION6 (click). The stategraph wastes 4-5 actions per state trying movement (Priority 2). For click-only games, skip movement entirely.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: In `_choose_action()`, check `available_actions`. If only ACTION6 → skip untried_movement priority. All actions are clicks.
- **Expected impact**: Doubles effective click budget.

### 8. [Puzzle Logic] Try clicking same object until state stabilizes
- **Hypothesis**: vc33 might require clicking the same object multiple times (e.g., adjusting a height N steps). The stategraph marks each (state, click_position) as "tried" and moves on. Instead, click the same interactive object repeatedly until the frame stops changing.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After a productive click (>10 cells changed), immediately re-click the same position. Continue until frame change < 10 cells (stabilized). Then move to next object.
- **Expected impact**: Completes multi-click adjustments that single clicks can't.

### 9. [Puzzle Logic] Size-ordered clicking — smallest interactive objects first
- **Hypothesis**: In puzzle games, smaller objects are often "buttons" and larger objects are "displays." Clicking smallest interactive objects first may trigger the correct game mechanic.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Sort click targets by size (ascending). Click smallest first. Track which sizes produce score increases.
- **Expected impact**: Prioritizes button-like objects over display objects.

### 10. [Frame Analysis] Grid region clustering — identify distinct puzzle areas
- **Hypothesis**: vc33's grid likely has distinct regions: interactive area, display area, status bar, border. Identifying these regions helps the agent focus clicks on the interactive area only.
- **Files to modify**: `src/arcagi3/utils/formatting.py`
- **Changes**: Segment grid into regions by color/spatial clustering. Identify: (a) status bar (row 0), (b) border/frame (consistent-color edges), (c) interactive area (where clicks produce changes), (d) display/reference area (static content).
- **Expected impact**: Focuses clicks on the right area, reducing wasted lives.

### 11. [Cross-Level Transfer] Remember productive click colors across levels
- **Hypothesis**: In vc33, the same color objects are interactive across levels. If color 9 is interactive on level 1, it's likely interactive on level 2. Carry this knowledge forward.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: On level transition, preserve: which colors were productive, which sizes were interactive, which regions contained clickable objects. On new level, prioritize these.
- **Expected impact**: Faster level 2+ exploration.

### 12. [Life Management] LS20 health-aware exploration — stop before dying
- **Hypothesis**: LS20 has health drain. The agent should detect remaining health (likely in status bar) and stop exploring when health is critical. Instead of dying, try to stay alive and exploit known-good paths.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Parse LS20 health from grid. When health < 20%, switch to conservative mode: only traverse known-safe transitions in the state graph.
- **Expected impact**: Prevents GAME_OVER, preserves actions for known-good paths.

### 13. [Puzzle Logic] Spatial relationship tracking — which objects affect which
- **Hypothesis**: In vc33, clicking object A might change object B (265 cell change). Tracking which objects affect which others reveals the puzzle structure. "Click A → B changes" + "Click B → C changes" = a chain to follow.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: After each click, identify which OTHER connected components changed. Build a graph: click_target → affected_objects. Use this to plan click sequences.
- **Expected impact**: Reveals puzzle structure for targeted solving.

### 14. [State Graph Navigation] Depth-limited search from productive states
- **Hypothesis**: When the agent finds a state where a click produced a large effect, do a depth-limited search (3-5 actions) from that state. This explores variations of the productive click sequence without wandering too far.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: When a click changes > 100 cells, mark that state as "interesting." Do 3-5 click variations from that state before moving on.
- **Expected impact**: Deeper exploration of promising states.

### 15. [Click Target Detection] Edge-adjacent object priority
- **Hypothesis**: In many puzzle games, interactive buttons are near the edges of the game area (not in the center, which is the display). Prioritize objects closer to grid edges.
- **Files to modify**: `src/arcagi3/stategraph_agent/agent.py`
- **Changes**: Score click targets by distance from center (farther = higher priority). Edge-adjacent objects first.
- **Expected impact**: Finds interactive buttons faster.

---

## Completed

- **Stategraph 001-017**: All score 0. See log. Key findings: vc33 clicks work (color 9 interactive), ft09 broken, both games have life mechanics, programmatic exploration ceiling, click strategies exhausted, Qwen3.5 can't reason.
- **Explorer 001-030**: All score 0. See log_archive_explorer.md.
