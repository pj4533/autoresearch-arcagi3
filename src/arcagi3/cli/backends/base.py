"""Backend interface for ARC-AGI-3 game execution."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ACTION_MAP = {
    "move_up": "ACTION1",
    "move_down": "ACTION2",
    "move_left": "ACTION3",
    "move_right": "ACTION4",
    "perform": "ACTION5",
    "click": "ACTION6",
    "undo": "ACTION7",
}

REVERSE_ACTION_MAP = {v: k for k, v in ACTION_MAP.items()}


@dataclass
class GameFrame:
    """Snapshot of game state after an action."""
    grids: List[List[List[int]]]
    state: str  # IN_PROGRESS, WIN, GAME_OVER
    levels_completed: int
    available_actions: List[str]  # human-readable: move_up, move_down, etc.
    guid: Optional[str] = None


class GameBackend(ABC):
    """Abstract base for game execution backends."""

    @abstractmethod
    def list_games(self) -> List[Dict[str, Any]]:
        """Return list of available games as [{"game_id": ..., "title": ...}, ...]."""

    @abstractmethod
    def open_scorecard(self, game_ids: List[str]) -> str:
        """Open a scorecard for tracking. Returns card_id."""

    @abstractmethod
    def close_scorecard(self) -> Dict[str, Any]:
        """Close the current scorecard. Returns summary."""

    @abstractmethod
    def reset(self, game_id: str) -> GameFrame:
        """Reset/start a game. Returns initial frame."""

    @abstractmethod
    def action(self, action_name: str, x: int = 0, y: int = 0) -> GameFrame:
        """Execute an action. Returns resulting frame."""

    @abstractmethod
    def get_state(self) -> GameFrame:
        """Get current game state without taking an action."""
