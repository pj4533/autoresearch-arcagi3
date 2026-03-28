from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from arcagi3.agent import HUMAN_ACTIONS, HUMAN_ACTIONS_LIST, MultimodalAgent
from arcagi3.prompts import PromptManager
from arcagi3.schemas import GameStep
from arcagi3.utils.context import SessionContext
from arcagi3.utils.formatting import grid_to_text_matrix
from arcagi3.utils.image import grid_to_image, image_to_base64, make_image_block
from arcagi3.utils.parsing import extract_json_from_response

logger = logging.getLogger(__name__)

# Phases
PHASE_PROBE = "probe"
PHASE_EXPLORE = "explore"
PHASE_EXPLOIT = "exploit"

# Number of actions to spend in probe phase (try each action once)
PROBE_ACTION_COUNT = 5  # ACTION1-5 (movement + perform action)


class ExplorerAgent(MultimodalAgent):
    """
    Explorer Agent: Probe -> Explore -> Exploit

    Phases:
    1. PROBE: Systematically try each available action once without LLM calls.
       Records frame changes to build an action-effect map. Zero LLM cost.
    2. EXPLORE: Feed frames + accumulated knowledge to LLM. Form hypotheses
       about game rules and goals. Choose actions based on analysis.
    3. EXPLOIT: When confident about the goal, execute plans efficiently.

    Datastore keys:
    - "phase": current phase (probe/explore/exploit)
    - "action_effects": dict mapping action names to observed effects
    - "hypotheses": current hypotheses about game rules
    - "memory": accumulated memory/scratchpad
    - "probe_index": which probe action we're on
    - "previous_action": last action taken
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

        if memory_word_limit is not None:
            self.memory_word_limit = memory_word_limit
        else:
            try:
                self.memory_word_limit = int(
                    getattr(self.provider.model_config, "kwargs", {}).get(
                        "memory_word_limit", 500
                    )
                )
            except Exception:
                self.memory_word_limit = 500

    def _get_want_vision(self, context: SessionContext) -> bool:
        _SENTINEL = object()
        want_vision = context.datastore.get("want_vision", _SENTINEL)
        if want_vision is _SENTINEL:
            want_vision = self.use_vision and bool(
                getattr(self.provider.model_config, "is_multimodal", False)
            )
            context.datastore["want_vision"] = want_vision
        return want_vision

    def _init_datastore(self, context: SessionContext) -> None:
        """Initialize datastore with defaults if not already set."""
        if "phase" not in context.datastore:
            context.datastore["phase"] = PHASE_PROBE
        if "action_effects" not in context.datastore:
            context.datastore["action_effects"] = {}
        if "hypotheses" not in context.datastore:
            context.datastore["hypotheses"] = ""
        if "memory" not in context.datastore:
            context.datastore["memory"] = ""
        if "probe_index" not in context.datastore:
            context.datastore["probe_index"] = 0

    def _get_available_action_names(self, context: SessionContext) -> List[str]:
        """Get ordered list of available action names."""
        if context.game.available_actions:
            indices = [int(str(a)) for a in context.game.available_actions]
            return [
                HUMAN_ACTIONS_LIST[i - 1]
                for i in indices
                if 1 <= i <= len(HUMAN_ACTIONS_LIST)
            ]
        return list(HUMAN_ACTIONS_LIST)

    def _save_current_frame(self, context: SessionContext) -> None:
        """Save current frame grid to datastore for next step's comparison."""
        grid = context.last_frame_grid
        if grid:
            context.datastore["saved_prev_grid"] = [row[:] for row in grid]

    def _describe_frame_change(self, context: SessionContext) -> str:
        """Compare saved previous frame to current frame to describe what changed."""
        prev = context.datastore.get("saved_prev_grid")
        curr_grids = context.frames.frame_grids
        curr = curr_grids[-1] if curr_grids else None

        if not prev or not curr:
            return "no previous frame to compare"

        if prev == curr:
            return "no visible change"

        # Count changed cells
        changes = 0
        total = 0
        for r_prev, r_curr in zip(prev, curr):
            for c_prev, c_curr in zip(r_prev, r_curr):
                total += 1
                if c_prev != c_curr:
                    changes += 1

        if changes == 0:
            return "no visible change"

        pct = (changes / total * 100) if total > 0 else 0
        return f"{changes} cells changed ({pct:.1f}% of grid)"

    def _probe_step(self, context: SessionContext) -> GameStep:
        """
        Probe phase: try each action systematically, no LLM calls.
        Returns the next probe action.
        """
        probe_index = context.datastore.get("probe_index", 0)
        available = self._get_available_action_names(context)

        # Record effect of previous probe action
        prev_action = context.datastore.get("previous_action")
        if prev_action:
            effect = self._describe_frame_change(context)
            action_effects = context.datastore.get("action_effects", {})
            action_effects[prev_action] = effect
            context.datastore["action_effects"] = action_effects
            logger.info(f"Probe: {prev_action} -> {effect}")

        # Filter to non-click, non-undo actions for probing (ACTION1-5)
        probe_actions = [a for a in available if a in ("ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5")]

        if probe_index >= len(probe_actions):
            # Probe phase complete, transition to explore
            context.datastore["phase"] = PHASE_EXPLORE
            context.datastore["probe_index"] = 0
            logger.info("Probe phase complete. Transitioning to explore.")
            return self._explore_step(context)

        action_name = probe_actions[probe_index]
        context.datastore["probe_index"] = probe_index + 1
        context.datastore["previous_action"] = action_name

        # Save current frame for next step's comparison
        self._save_current_frame(context)

        return GameStep(
            action={"action": action_name},
            reasoning={
                "phase": PHASE_PROBE,
                "action": action_name,
                "probe_index": probe_index,
                "description": f"Probing {HUMAN_ACTIONS.get(action_name, action_name)}",
            },
        )

    def _explore_step(self, context: SessionContext) -> GameStep:
        """
        Explore phase: use LLM to analyze state, form hypotheses, choose actions.
        """
        # Record effect of previous action
        prev_action = context.datastore.get("previous_action")
        if prev_action:
            effect = self._describe_frame_change(context)
            action_effects = context.datastore.get("action_effects", {})
            action_effects[prev_action] = effect
            context.datastore["action_effects"] = action_effects

        want_vision = self._get_want_vision(context)

        # Build available actions description
        available = self._get_available_action_names(context)
        actions_desc = "\n".join(
            f"  - {HUMAN_ACTIONS.get(a, a)}" for a in available
        )

        # Render explore prompt
        explore_prompt = self.prompt_manager.render(
            "explore",
            {
                "action_count": context.game.action_counter,
                "max_actions": self.max_actions,
                "current_score": context.game.current_score,
                "phase": context.datastore.get("phase", PHASE_EXPLORE),
                "action_effects": context.datastore.get("action_effects", {}),
                "hypotheses": context.datastore.get("hypotheses", ""),
                "memory": context.datastore.get("memory", ""),
                "available_actions": actions_desc,
            },
        )

        # Build message content
        content: List[Dict[str, Any]] = []
        if want_vision:
            for img in context.frame_images:
                content.append(make_image_block(image_to_base64(img)))
        else:
            for i, grid in enumerate(context.frames.frame_grids):
                content.append(
                    {"type": "text", "text": f"Frame {i}:\n{grid_to_text_matrix(grid)}"}
                )
        content.append({"type": "text", "text": explore_prompt})

        messages = [
            {
                "role": "system",
                "content": self.prompt_manager.render(
                    "system", {"use_vision": want_vision}
                ),
            },
            {"role": "user", "content": content},
        ]

        # Call LLM
        response = self.provider.call_with_tracking(
            context, messages, step_name="explore"
        )
        response_text = self.provider.extract_content(response)

        # Parse response
        try:
            result = extract_json_from_response(response_text)
        except Exception as e:
            logger.warning(f"Failed to parse explore response: {e}")
            # Fallback: try a movement action
            result = {"action": "Move Up", "reasoning": "Fallback due to parse error"}

        # Update hypotheses and memory
        if result.get("hypothesis"):
            context.datastore["hypotheses"] = result["hypothesis"]
        if result.get("observation"):
            memory = context.datastore.get("memory", "")
            new_entry = f"Action {context.game.action_counter}: {result.get('observation', '')}"
            if memory:
                # Keep memory bounded
                lines = memory.split("\n")
                if len(lines) > 20:
                    lines = lines[-15:]
                memory = "\n".join(lines)
                memory = f"{memory}\n{new_entry}"
            else:
                memory = new_entry
            context.datastore["memory"] = memory

        # Convert human action to game action
        human_action = result.get("action", "Move Up")
        game_action = self._convert_to_game_action(context, str(human_action))

        context.datastore["previous_action"] = game_action.get("action", "")

        # Save current frame for next step's comparison
        self._save_current_frame(context)

        reasoning = {
            "phase": context.datastore.get("phase", PHASE_EXPLORE),
            "observation": str(result.get("observation", ""))[:500],
            "analysis": str(result.get("analysis", ""))[:500],
            "hypothesis": str(result.get("hypothesis", ""))[:500],
            "human_action": human_action,
        }

        return GameStep(action=game_action, reasoning=reasoning)

    def _convert_to_game_action(
        self, context: SessionContext, human_action: str
    ) -> Dict[str, Any]:
        """Convert a human-readable action to a game action dict."""
        # Try direct mapping first
        action_map = {v.lower(): k for k, v in HUMAN_ACTIONS.items()}
        direct = action_map.get(human_action.lower())
        if direct:
            return {"action": direct}

        # Use LLM for conversion
        if context.game.available_actions:
            indices = [int(str(a)) for a in context.game.available_actions]
            action_list = "\n".join(
                f"{HUMAN_ACTIONS_LIST[i - 1]} = {HUMAN_ACTIONS[HUMAN_ACTIONS_LIST[i - 1]]}"
                for i in indices
                if 1 <= i <= len(HUMAN_ACTIONS_LIST)
            )
            valid_actions = ", ".join(
                HUMAN_ACTIONS_LIST[i - 1]
                for i in indices
                if 1 <= i <= len(HUMAN_ACTIONS_LIST)
            )
        else:
            action_list = "\n".join(
                f"{name} = {desc}" for name, desc in HUMAN_ACTIONS.items()
            )
            valid_actions = ", ".join(HUMAN_ACTIONS_LIST)

        want_vision = self._get_want_vision(context)
        convert_prompt = self.prompt_manager.render(
            "convert",
            {
                "action_list": action_list,
                "valid_actions": valid_actions,
            },
        )

        content: List[Dict[str, Any]] = []
        if want_vision:
            img = context.last_frame_image()
            if img is not None:
                content.append(make_image_block(image_to_base64(img)))
        else:
            if context.last_frame_grid is not None:
                content.append(
                    {
                        "type": "text",
                        "text": f"Current frame:\n{grid_to_text_matrix(context.last_frame_grid)}",
                    }
                )
        content.append({"type": "text", "text": human_action + "\n\n" + convert_prompt})

        messages = [
            {
                "role": "system",
                "content": self.prompt_manager.render(
                    "system", {"use_vision": want_vision}
                ),
            },
            {"role": "user", "content": content},
        ]

        response = self.provider.call_with_tracking(
            context, messages, step_name="convert"
        )
        response_text = self.provider.extract_content(response)

        try:
            result = extract_json_from_response(response_text)
            action_name = result.get("action")
            if action_name and str(action_name).startswith("ACTION"):
                return result
        except Exception as e:
            logger.warning(f"Failed to parse convert response: {e}")

        # Final fallback
        return {"action": "ACTION1"}

    def step(self, context: SessionContext) -> GameStep:
        """Main step dispatch based on current phase."""
        self._init_datastore(context)
        phase = context.datastore.get("phase", PHASE_PROBE)

        if phase == PHASE_PROBE:
            return self._probe_step(context)
        else:
            return self._explore_step(context)


__all__ = ["ExplorerAgent"]
