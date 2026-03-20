from __future__ import annotations

from arcagi3.explorer_agent import ExplorerAgent

definition = {
    "name": "explorer",
    "description": "Probe-Explore-Exploit agent with action-effect mapping",
    "agent_class": ExplorerAgent,
}

agents = [definition]

__all__ = ["definition", "agents"]
