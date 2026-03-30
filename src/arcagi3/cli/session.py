"""Session state management for the ARC CLI."""
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SESSION_DIR = ".arc_session"
SESSION_FILE = os.path.join(SESSION_DIR, "session.json")
SCORECARD_FILE = os.path.join(SESSION_DIR, "scorecard.json")


@dataclass
class Session:
    """Persistent session state between CLI invocations."""
    game_id: str
    backend: str  # "api" or "local"
    card_id: Optional[str] = None
    guid: Optional[str] = None
    max_actions: int = 40
    action_count: int = 0
    current_score: int = 0
    current_state: str = "IN_PROGRESS"
    previous_frame: Optional[List[List[List[int]]]] = None
    action_history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.current_state not in ("WIN", "GAME_OVER")

    @property
    def actions_remaining(self) -> int:
        if self.max_actions <= 0:
            return -1  # unlimited
        return max(0, self.max_actions - self.action_count)

    def record_action(self, action_name: str, frame, x: int = 0, y: int = 0):
        """Record an action and update state from the resulting frame."""
        self.action_count += 1
        self.previous_frame = frame.grids[-1] if frame.grids else None
        self.current_score = frame.levels_completed
        self.current_state = frame.state
        self.guid = frame.guid or self.guid

        entry = {"action_name": action_name}
        if action_name == "click":
            entry["x"] = x
            entry["y"] = y
        self.action_history.append(entry)

    def save(self):
        """Save session to disk."""
        os.makedirs(SESSION_DIR, exist_ok=True)
        data = asdict(self)
        with open(SESSION_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "Session":
        """Load session from disk. Raises if no session exists."""
        if not os.path.exists(SESSION_FILE):
            raise FileNotFoundError(
                "No active session. Start one with: arc start <game_id>"
            )
        with open(SESSION_FILE) as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def exists(cls) -> bool:
        return os.path.exists(SESSION_FILE)

    @classmethod
    def delete(cls):
        """Remove session file."""
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        # Don't remove SESSION_DIR if scorecard.json still exists
        remaining = [f for f in os.listdir(SESSION_DIR) if f != "frame.png"] if os.path.exists(SESSION_DIR) else []
        if os.path.exists(SESSION_DIR) and not remaining:
            os.rmdir(SESSION_DIR)


@dataclass
class ScorecardSession:
    """Multi-game scorecard state that persists across individual game sessions."""
    card_id: str
    backend: str
    game_list: List[str]
    current_game_index: int = 0
    completed_games: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    status: str = "open"  # "open", "closed"
    max_actions_per_game: int = 40
    experiment_id: str = ""

    @property
    def current_game(self) -> Optional[str]:
        if self.current_game_index < len(self.game_list):
            return self.game_list[self.current_game_index]
        return None

    @property
    def games_completed(self) -> int:
        return len(self.completed_games)

    @property
    def games_total(self) -> int:
        return len(self.game_list)

    @property
    def is_complete(self) -> bool:
        return self.games_completed >= self.games_total

    @property
    def running_score(self) -> float:
        if not self.completed_games:
            return 0.0
        scores = [g.get("score", 0) for g in self.completed_games.values()]
        return sum(scores) / len(scores)

    def record_game(self, game_id: str, score: float, actions: int,
                    levels_completed: int, state: str):
        self.completed_games[game_id] = {
            "score": score,
            "actions": actions,
            "levels_completed": levels_completed,
            "state": state,
        }

    def advance(self):
        self.current_game_index += 1

    def save(self):
        os.makedirs(SESSION_DIR, exist_ok=True)
        data = asdict(self)
        with open(SCORECARD_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "ScorecardSession":
        if not os.path.exists(SCORECARD_FILE):
            raise FileNotFoundError("No active scorecard. Open one with: arc scorecard open")
        with open(SCORECARD_FILE) as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def exists(cls) -> bool:
        return os.path.exists(SCORECARD_FILE)

    @classmethod
    def delete(cls):
        if os.path.exists(SCORECARD_FILE):
            os.remove(SCORECARD_FILE)
