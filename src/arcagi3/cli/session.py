"""Session state management for the ARC CLI."""
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SESSION_DIR = ".arc_session"
SESSION_FILE = os.path.join(SESSION_DIR, "session.json")


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
        if os.path.exists(SESSION_DIR) and not os.listdir(SESSION_DIR):
            os.rmdir(SESSION_DIR)
