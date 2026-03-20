"""API backend — talks to three.arcprize.org via GameClient."""
from typing import Any, Dict, List, Optional

from arcagi3.game_client import GameClient
from arcagi3.cli.backends.base import (
    ACTION_MAP,
    REVERSE_ACTION_MAP,
    GameBackend,
    GameFrame,
)


class APIBackend(GameBackend):
    """Backend that communicates with the ARC-AGI-3 API server."""

    def __init__(self):
        self.client = GameClient()
        self.card_id: Optional[str] = None
        self.game_id: Optional[str] = None
        self.guid: Optional[str] = None
        self._last_frame: Optional[GameFrame] = None

    def _to_game_frame(self, resp: Dict[str, Any]) -> GameFrame:
        raw_actions = resp.get("available_actions", [])
        available = []
        for a in raw_actions:
            name = REVERSE_ACTION_MAP.get(a)
            if name:
                available.append(name)

        grids = resp.get("frame", [])
        # Ensure grids are plain lists (not numpy)
        if grids and hasattr(grids[0], "tolist"):
            grids = [g.tolist() for g in grids]

        return GameFrame(
            grids=grids,
            state=resp.get("state", "IN_PROGRESS"),
            levels_completed=resp.get("levels_completed", 0),
            available_actions=available,
            guid=resp.get("guid"),
        )

    def list_games(self) -> List[Dict[str, Any]]:
        return self.client.list_games()

    def open_scorecard(self, game_ids: List[str]) -> str:
        resp = self.client.open_scorecard(game_ids)
        self.card_id = resp.get("card_id")
        return self.card_id

    def close_scorecard(self) -> Dict[str, Any]:
        if not self.card_id:
            return {}
        return self.client.close_scorecard(self.card_id)

    def reset(self, game_id: str) -> GameFrame:
        self.game_id = game_id
        resp = self.client.reset_game(self.card_id, game_id, guid=self.guid)
        self.guid = resp.get("guid")
        frame = self._to_game_frame(resp)
        self._last_frame = frame
        return frame

    def action(self, action_name: str, x: int = 0, y: int = 0) -> GameFrame:
        code = ACTION_MAP[action_name]
        data: Dict[str, Any] = {"game_id": self.game_id}
        if self.guid:
            data["guid"] = self.guid
        if code == "ACTION6":
            data["x"] = x
            data["y"] = y
        resp = self.client.execute_action(code, data)
        self.guid = resp.get("guid", self.guid)
        frame = self._to_game_frame(resp)
        self._last_frame = frame
        return frame

    def get_state(self) -> GameFrame:
        if self._last_frame is None:
            raise RuntimeError("No game state available. Start a game first.")
        return self._last_frame
