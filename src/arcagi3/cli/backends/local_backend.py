"""Local backend — uses arc-agi package with arcengine for fast local execution."""
import io
import logging
import sys
from typing import Any, Dict, List, Optional

import arc_agi
from arcengine import GameAction as EngineAction, GameState

from arcagi3.cli.backends.base import GameBackend, GameFrame


# Map human-readable action names to arcengine GameAction enum values
ACTION_TO_ENGINE = {
    "move_up": EngineAction.ACTION1,
    "move_down": EngineAction.ACTION2,
    "move_left": EngineAction.ACTION3,
    "move_right": EngineAction.ACTION4,
    "perform": EngineAction.ACTION5,
    "click": EngineAction.ACTION6,
    "undo": EngineAction.ACTION7,
}

# Reverse: engine action int value → human name
_ENGINE_VALUE_TO_NAME = {}
for _name, _action in ACTION_TO_ENGINE.items():
    _ENGINE_VALUE_TO_NAME[_action.value] = _name

# GameState → string
_STATE_MAP = {
    GameState.NOT_PLAYED: "NOT_PLAYED",
    GameState.NOT_FINISHED: "IN_PROGRESS",
    GameState.WIN: "WIN",
    GameState.GAME_OVER: "GAME_OVER",
}


class LocalBackend(GameBackend):
    """Backend using local arcengine for 2000+ FPS execution."""

    def __init__(self):
        # Arcade() logs to stdout during init; suppress it for clean CLI output
        _old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            self.arcade = arc_agi.Arcade()
        finally:
            sys.stdout = _old_stdout
        # Also suppress future arc_agi logs
        _arc_logger = logging.getLogger("arc_agi.base")
        _arc_logger.setLevel(logging.WARNING)
        for h in _arc_logger.handlers:
            h.setLevel(logging.WARNING)
        self.env = None
        self.game_id: Optional[str] = None
        self._last_frame: Optional[GameFrame] = None

    def _obs_to_frame(self, obs) -> GameFrame:
        """Convert arcengine observation to GameFrame."""
        grids = []
        if obs.frame:
            for arr in obs.frame:
                grids.append(arr.tolist() if hasattr(arr, "tolist") else arr)

        state_str = _STATE_MAP.get(obs.state, str(obs.state))

        available = []
        if obs.available_actions:
            for action_int in obs.available_actions:
                name = _ENGINE_VALUE_TO_NAME.get(action_int)
                if name:
                    available.append(name)

        return GameFrame(
            grids=grids,
            state=state_str,
            levels_completed=obs.levels_completed,
            available_actions=available,
            guid=getattr(obs, "guid", None),
        )

    def list_games(self) -> List[Dict[str, Any]]:
        envs = self.arcade.get_environments()
        return [
            {"game_id": e.game_id, "title": getattr(e, "title", e.game_id)}
            for e in envs
        ]

    def open_scorecard(self, game_ids: List[str]) -> str:
        card_id = self.arcade.create_scorecard(tags=["arc-cli"])
        return card_id

    def close_scorecard(self) -> Dict[str, Any]:
        return {}

    def reset(self, game_id: str) -> GameFrame:
        self.game_id = game_id
        self.env = self.arcade.make(game_id)
        obs = self.env.step(EngineAction.RESET)
        frame = self._obs_to_frame(obs)
        self._last_frame = frame
        return frame

    def action(self, action_name: str, x: int = 0, y: int = 0) -> GameFrame:
        if self.env is None:
            raise RuntimeError("No game environment. Call reset() first.")
        engine_action = ACTION_TO_ENGINE[action_name]
        data = None
        if action_name == "click":
            data = {"x": x, "y": y}
        obs = self.env.step(engine_action, data=data)
        frame = self._obs_to_frame(obs)
        self._last_frame = frame
        return frame

    def get_state(self) -> GameFrame:
        if self.env is None:
            raise RuntimeError("No game environment. Start a game first.")
        obs = self.env.observation_space
        return self._obs_to_frame(obs)

    def replay_actions(self, game_id: str, action_history: List[Dict[str, Any]]) -> GameFrame:
        """Replay a sequence of actions to restore game state.

        Used to reconstruct local game state between CLI invocations.
        At 2000+ FPS this is nearly instant even for 100+ actions.
        """
        frame = self.reset(game_id)
        for entry in action_history:
            name = entry["action_name"]
            x = entry.get("x", 0)
            y = entry.get("y", 0)
            frame = self.action(name, x=x, y=y)
        return frame
