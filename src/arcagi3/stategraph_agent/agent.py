"""
State Graph Agent: Programmatic exploration with occasional LLM hypothesis calls.

Instead of calling the LLM every step, this agent:
1. Hashes frames to build a state graph
2. Systematically tries untried actions in each state
3. Tracks which actions cause frame changes and score increases
4. Only calls the LLM every N steps for high-level hypothesis formation
5. Detects loops and escapes them with random walks
"""
from __future__ import annotations

import hashlib
import logging
import random
from typing import Any, Dict, List, Optional

from arcagi3.agent import HUMAN_ACTIONS, HUMAN_ACTIONS_LIST, MultimodalAgent
from arcagi3.prompts import PromptManager
from arcagi3.schemas import GameStep
from arcagi3.utils.context import SessionContext
from arcagi3.utils.formatting import (
    describe_frame_change_detailed,
    detect_interactive_objects,
    grid_to_structured_description,
)
from arcagi3.utils.parsing import extract_json_from_response

logger = logging.getLogger(__name__)

# How often to call the LLM for hypothesis formation (0 = disabled)
LLM_INTERVAL = 0
# Max states before evicting least-visited
MAX_STATES = 500
# Status bar rows to mask when hashing frames
STATUS_BAR_ROWS = 2


class StateGraphAgent(MultimodalAgent):
    """
    Programmatic state-graph explorer.

    Builds a directed graph of game states (hashed frames) and transitions
    (actions). Systematically tries every action in every state. Calls the
    LLM only occasionally for high-level hypothesis formation.
    """

    def __init__(
        self,
        *args,
        use_vision: bool = True,
        show_images: bool = False,
        memory_word_limit: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.prompt_manager = PromptManager()
        self.use_vision = use_vision
        self.show_images = show_images

    def _init_datastore(self, context: SessionContext) -> None:
        """Initialize datastore with defaults if not already set."""
        defaults = {
            "state_graph": {},          # {hash: {transitions: {}, visit_count: 0, score: 0}}
            "prev_state_hash": None,
            "prev_action": None,
            "step_counter": 0,
            "winning_actions": [],      # Actions that caused score increases
            "winning_sequences": [],    # Full sequences that solved levels
            "current_sequence": [],     # Actions taken this level
            "click_targets": [],        # Detected interactive objects
            "click_queue": [],          # Click targets to try
            "click_results": {},        # "x,y" -> "changed"|"no_change"
            "action_knowledge": {},     # action_type -> observed effect
            "prev_score": 0,
            "llm_hypothesis": "",
            "random_walk_remaining": 0,
            "balance_buttons": None,    # Detected balance puzzle buttons [(x,y), (x,y)]
            "balance_mode": False,      # Whether balance puzzle strategy is active
            "balance_target_btn": None, # Which button to keep clicking (locked after first detection)
        }
        for key, default in defaults.items():
            if key not in context.datastore:
                context.datastore[key] = default

    def _hash_frame(self, grid: List[List[int]]) -> str:
        """Hash frame grid, masking status bar rows."""
        if not grid:
            return "empty"
        inner = grid[STATUS_BAR_ROWS:-STATUS_BAR_ROWS] if len(grid) > 2 * STATUS_BAR_ROWS else grid
        return hashlib.md5(str(inner).encode()).hexdigest()[:16]

    def _get_available_actions(self, context: SessionContext) -> List[str]:
        """Get list of available ACTION names."""
        if context.game.available_actions:
            indices = [int(str(a)) for a in context.game.available_actions]
            return [
                HUMAN_ACTIONS_LIST[i - 1]
                for i in indices
                if 1 <= i <= len(HUMAN_ACTIONS_LIST)
            ]
        return list(HUMAN_ACTIONS_LIST)

    def _get_state_node(self, context: SessionContext, state_hash: str) -> dict:
        """Get or create a state node in the graph."""
        graph = context.datastore["state_graph"]
        if state_hash not in graph:
            # Evict least-visited if at capacity
            if len(graph) >= MAX_STATES:
                least = min(graph.items(), key=lambda kv: kv[1]["visit_count"])
                del graph[least[0]]
            graph[state_hash] = {"transitions": {}, "visit_count": 0, "score": 0}
        return graph[state_hash]

    def _record_transition(self, context: SessionContext, current_hash: str) -> None:
        """Record the transition from previous state via previous action."""
        prev_hash = context.datastore.get("prev_state_hash")
        prev_action = context.datastore.get("prev_action")
        if prev_hash and prev_action:
            prev_node = self._get_state_node(context, prev_hash)
            prev_grid = context.datastore.get("saved_prev_grid")
            curr_grid = context.last_frame_grid

            # Record whether frame changed
            frame_changed = prev_hash != current_hash
            prev_node["transitions"][prev_action] = {
                "target": current_hash,
                "frame_changed": frame_changed,
            }

            # Update action knowledge
            knowledge = context.datastore["action_knowledge"]
            action_type = prev_action
            if frame_changed:
                if prev_grid and curr_grid:
                    desc = describe_frame_change_detailed(prev_grid, curr_grid)
                    knowledge[action_type] = desc
                else:
                    knowledge[action_type] = "frame changed"
            elif action_type not in knowledge:
                knowledge[action_type] = "no visible change"

    def _check_score_change(self, context: SessionContext) -> bool:
        """Check if score increased, handle level transitions."""
        current_score = context.game.current_score
        prev_score = context.datastore.get("prev_score", 0)

        if current_score > prev_score:
            # Score increased!
            prev_action = context.datastore.get("prev_action")
            if prev_action:
                context.datastore["winning_actions"].append(prev_action)
                logger.info(f"SCORE INCREASE: {prev_score} -> {current_score} via {prev_action}")

            # Save the winning sequence for cross-level transfer
            seq = context.datastore["current_sequence"]
            if seq:
                context.datastore["winning_sequences"].append(list(seq))

            # Clear state graph for new level, preserve action knowledge
            context.datastore["state_graph"] = {}
            context.datastore["prev_state_hash"] = None
            context.datastore["current_sequence"] = []
            context.datastore["click_queue"] = []
            context.datastore["click_results"] = {}
            context.datastore["random_walk_remaining"] = 0
            context.datastore["balance_buttons"] = None
            context.datastore["balance_target_btn"] = None

            context.datastore["prev_score"] = current_score
            return True

        context.datastore["prev_score"] = current_score
        return False

    def _choose_action(self, context: SessionContext, state_hash: str) -> Dict[str, Any]:
        """Choose next action programmatically. No LLM call."""
        available = self._get_available_actions(context)
        node = self._get_state_node(context, state_hash)
        tried = set(node["transitions"].keys())
        untried = [a for a in available if a not in tried]

        # Priority 0: Continue random walk if in progress
        if context.datastore["random_walk_remaining"] > 0:
            context.datastore["random_walk_remaining"] -= 1
            action = random.choice(available)
            return self._make_action(action, context)

        # Priority 1: Replay winning sequence on new levels
        sequences = context.datastore.get("winning_sequences", [])
        current_seq = context.datastore.get("current_sequence", [])
        if sequences and len(current_seq) < len(sequences[-1]):
            replay_action = sequences[-1][len(current_seq)]
            if replay_action in available:
                return self._make_action(replay_action, context)

        # Priority 2: Try untried non-click actions first
        untried_movement = [a for a in untried if a != "ACTION6"]
        if untried_movement:
            return self._make_action(untried_movement[0], context)

        # Priority 2.5: Balance puzzle strategy (vc33-style)
        balance_action = self._detect_balance_puzzle(context)
        if balance_action:
            return balance_action

        # Priority 3: Try clicking at detected interactive objects
        if "ACTION6" in untried or "ACTION6" in available:
            click_action = self._try_click(context)
            if click_action:
                return click_action

        # Priority 4: Navigate to neighbor state with most untried actions
        graph = context.datastore["state_graph"]
        best_action = None
        best_untried_count = -1

        for action, trans in node["transitions"].items():
            target = trans["target"]
            if target in graph:
                target_node = graph[target]
                target_tried = set(target_node["transitions"].keys())
                target_available = set(available)
                target_untried = len(target_available - target_tried)
                if target_untried > best_untried_count:
                    best_untried_count = target_untried
                    best_action = action

        if best_action and best_untried_count > 0:
            return self._make_action(best_action, context)

        # Priority 5: Navigate to least-visited neighbor
        if node["transitions"]:
            least_visited_action = None
            min_visits = float("inf")
            for action, trans in node["transitions"].items():
                target = trans["target"]
                visits = graph.get(target, {}).get("visit_count", 0)
                if visits < min_visits:
                    min_visits = visits
                    least_visited_action = action
            if least_visited_action:
                return self._make_action(least_visited_action, context)

        # Priority 6: Random walk to escape (3-5 steps)
        context.datastore["random_walk_remaining"] = random.randint(2, 4)
        action = random.choice(available)
        return self._make_action(action, context)

    def _detect_balance_puzzle(self, context: SessionContext) -> Optional[Dict[str, Any]]:
        """Detect vc33-style balance puzzle and choose the right button.

        Balance puzzles have: two regions (upper/lower) separated by a bar,
        two buttons that adjust the boundary between regions. Goal: click
        the button that moves boundaries toward equilibrium.
        """
        grid = context.last_frame_grid
        if not grid:
            return None

        rows = len(grid)
        cols = len(grid[0]) if rows else 0

        # Only for click-only games
        available = self._get_available_actions(context)
        if available != ["ACTION6"]:
            return None

        # Find the gray bar (horizontal divider)
        # Look for rows that are mostly one non-bg color
        from collections import Counter
        bar_rows = []
        for r in range(2, rows - 2):
            row_colors = Counter(grid[r])
            # Gray bar: mostly color 5 (or any single non-bg color spanning >60% of row)
            for color, count in row_colors.items():
                if color not in (0, 3, 7) and count > cols * 0.4:
                    bar_rows.append(r)
                    break

        if len(bar_rows) < 2:
            return None

        bar_start = min(bar_rows)
        bar_end = max(bar_rows)

        # Find green/black boundary in upper region (above bar)
        upper_row = (2 + bar_start) // 2
        upper_boundary = -1
        for c in range(cols - 1, -1, -1):
            if grid[upper_row][c] == 3:
                upper_boundary = c
                break

        # Find green/black boundary in lower region (below bar)
        lower_row = (bar_end + 1 + rows - 2) // 2
        lower_boundary = -1
        for c in range(cols - 1, -1, -1):
            if grid[lower_row][c] == 3:
                lower_boundary = c
                break

        if upper_boundary < 0 or lower_boundary < 0:
            return None

        # Find the two maroon buttons (color 9 blocks)
        buttons = context.datastore.get("balance_buttons")
        if not buttons:
            c9_objects = []
            visited = set()
            for r in range(2, rows - 2):
                for c in range(cols):
                    if grid[r][c] == 9 and (r, c) not in visited:
                        # BFS to find connected component
                        component = []
                        queue = [(r, c)]
                        visited.add((r, c))
                        while queue:
                            cr, cc = queue.pop(0)
                            component.append((cc, cr))
                            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                                nr, nc = cr+dr, cc+dc
                                if 2 <= nr < rows-2 and 0 <= nc < cols and (nr,nc) not in visited and grid[nr][nc] == 9:
                                    visited.add((nr, nc))
                                    queue.append((nr, nc))
                        center_x = sum(p[0] for p in component) // len(component)
                        center_y = sum(p[1] for p in component) // len(component)
                        c9_objects.append((center_x, center_y))

            if len(c9_objects) >= 2:
                # Sort by y position: upper button first, lower button second
                c9_objects.sort(key=lambda p: p[1])
                buttons = c9_objects[:2]
                context.datastore["balance_buttons"] = buttons
                context.datastore["balance_mode"] = True
                logger.info(f"Balance puzzle detected: buttons at {buttons}, boundaries upper={upper_boundary} lower={lower_boundary}")

        if not buttons or len(buttons) < 2:
            return None

        # Strategy: click the button that moves boundaries toward each other
        # Upper button: decreases upper green, increases lower green
        # Lower button: increases upper green, decreases lower green
        # Goal: make boundaries converge (or cross)

        # Lock the target button on first detection — don't switch after boundaries cross
        locked_btn = context.datastore.get("balance_target_btn")
        if locked_btn is None:
            if upper_boundary < lower_boundary:
                locked_btn = buttons[1]  # Lower button: increases upper, decreases lower
            else:
                locked_btn = buttons[0]  # Upper button: decreases upper, increases lower
            context.datastore["balance_target_btn"] = locked_btn

        # Convert grid coords (0-63) to agent coords (0-127) since base agent does //2
        return {"action": "ACTION6", "x": min(locked_btn[0] * 2, 127), "y": min(locked_btn[1] * 2, 127)}

    def _try_click(self, context: SessionContext) -> Optional[Dict[str, Any]]:
        """Try clicking at the next untried interactive object."""
        click_queue = context.datastore.get("click_queue", [])
        click_results = context.datastore.get("click_results", {})

        # Populate click queue if empty
        if not click_queue:
            grid = context.last_frame_grid
            if grid:
                targets = detect_interactive_objects(grid)
                # Filter out already-tried positions
                new_targets = []
                for t in targets:
                    key = f"{t['x']},{t['y']}"
                    if key not in click_results:
                        new_targets.append(t)
                context.datastore["click_targets"] = targets
                context.datastore["click_queue"] = new_targets
                click_queue = new_targets

        if not click_queue:
            return None

        # Pop next target
        target = click_queue.pop(0)
        context.datastore["click_queue"] = click_queue

        key = f"{target['x']},{target['y']}"
        click_results[key] = "pending"
        context.datastore["click_results"] = click_results

        return {
            "action": "ACTION6",
            "x": target["x"],
            "y": target["y"],
        }

    def _make_action(self, action_name: str, context: SessionContext) -> Dict[str, Any]:
        """Create action dict for non-click actions."""
        if action_name == "ACTION6":
            # Default click at center if no specific target
            return {"action": "ACTION6", "x": 64, "y": 64}
        return {"action": action_name}

    def _maybe_call_llm(self, context: SessionContext, state_hash: str) -> Optional[str]:
        """Call LLM for hypothesis if it's time."""
        if LLM_INTERVAL <= 0:
            return None
        step_counter = context.datastore.get("step_counter", 0)
        if step_counter > 0 and step_counter % LLM_INTERVAL == 0:
            return self._call_llm_hypothesis(context, state_hash)
        return None

    def _call_llm_hypothesis(self, context: SessionContext, state_hash: str) -> Optional[str]:
        """Call LLM with state graph summary for hypothesis formation."""
        graph = context.datastore["state_graph"]
        node = self._get_state_node(context, state_hash)
        available = self._get_available_actions(context)
        tried = set(node["transitions"].keys())
        untried = [a for a in available if a not in tried]

        # Build transition info for prompt
        transitions = {}
        for action, trans in node["transitions"].items():
            target = trans["target"]
            transitions[action] = {
                "same_state": target == state_hash,
                "visits": graph.get(target, {}).get("visit_count", 0),
                "frame_changed": trans.get("frame_changed", False),
            }

        # Get frame description
        grid = context.last_frame_grid
        frame_desc = grid_to_structured_description(grid) if grid else "No frame available"

        try:
            prompt_text = self.prompt_manager.render(
                "hypothesis",
                {
                    "num_states": len(graph),
                    "current_visits": node["visit_count"],
                    "score": context.game.current_score,
                    "action_count": context.game.action_counter,
                    "max_actions": self.max_actions,
                    "transitions": transitions,
                    "untried_actions": ", ".join(untried) if untried else "none",
                    "frame_description": frame_desc,
                    "action_knowledge": context.datastore.get("action_knowledge", {}),
                },
            )

            messages = [
                {
                    "role": "system",
                    "content": self.prompt_manager.render("system", {}),
                },
                {"role": "user", "content": prompt_text},
            ]

            response = self.provider.call_with_tracking(
                context, messages, step_name="hypothesis"
            )
            response_text = self.provider.extract_content(response)

            try:
                result = extract_json_from_response(response_text)
                hypothesis = result.get("hypothesis", "")
                context.datastore["llm_hypothesis"] = hypothesis
                logger.info(f"LLM hypothesis: {hypothesis}")
                return hypothesis
            except Exception:
                logger.warning("Failed to parse LLM hypothesis response")
                return None

        except Exception as e:
            logger.warning(f"LLM hypothesis call failed: {e}")
            return None

    def _save_current_frame(self, context: SessionContext) -> None:
        """Save current frame grid for next step's comparison."""
        grid = context.last_frame_grid
        if grid:
            context.datastore["saved_prev_grid"] = [row[:] for row in grid]

    def _update_click_results(self, context: SessionContext, current_hash: str) -> None:
        """Update click results based on whether frame changed after a click."""
        prev_action = context.datastore.get("prev_action")
        prev_hash = context.datastore.get("prev_state_hash")
        if prev_action != "ACTION6" or not prev_hash:
            return

        click_results = context.datastore.get("click_results", {})
        # Find the pending click result
        for key, status in click_results.items():
            if status == "pending":
                click_results[key] = "changed" if current_hash != prev_hash else "no_change"
                break
        context.datastore["click_results"] = click_results

    def step(self, context: SessionContext) -> GameStep:
        """Main step: programmatic exploration with occasional LLM calls."""
        self._init_datastore(context)

        # Get current frame and hash it
        grid = context.last_frame_grid
        if not grid:
            return GameStep(
                action={"action": "ACTION1"},
                reasoning={"phase": "no_frame", "description": "No frame available"},
            )

        current_hash = self._hash_frame(grid)
        node = self._get_state_node(context, current_hash)
        node["visit_count"] += 1
        node["score"] = context.game.current_score

        # Record transition from previous step
        self._record_transition(context, current_hash)

        # Update click results
        self._update_click_results(context, current_hash)

        # Check for score changes / level transitions
        level_changed = self._check_score_change(context)
        if level_changed:
            # Re-hash after level transition (graph was cleared)
            current_hash = self._hash_frame(grid)
            node = self._get_state_node(context, current_hash)
            node["visit_count"] += 1

        # Maybe call LLM for hypothesis
        step_counter = context.datastore["step_counter"]
        self._maybe_call_llm(context, current_hash)
        context.datastore["step_counter"] = step_counter + 1

        # Choose action programmatically
        action = self._choose_action(context, current_hash)

        # Track state
        context.datastore["prev_state_hash"] = current_hash
        context.datastore["prev_action"] = action.get("action", "")
        context.datastore["current_sequence"].append(action.get("action", ""))

        # Save frame for next step's comparison
        self._save_current_frame(context)

        # Build reasoning for logging
        graph = context.datastore["state_graph"]
        available = self._get_available_actions(context)
        tried = set(node["transitions"].keys())
        untried = [a for a in available if a not in tried]

        reasoning = {
            "phase": "stategraph",
            "states_visited": len(graph),
            "current_state_visits": node["visit_count"],
            "untried_in_state": len(untried),
            "action": action.get("action", ""),
            "hypothesis": context.datastore.get("llm_hypothesis", "")[:200],
            "score": context.game.current_score,
        }

        return GameStep(action=action, reasoning=reasoning)


__all__ = ["StateGraphAgent"]
