from __future__ import annotations

from arcagi3.stategraph_agent import StateGraphAgent

definition = {
    "name": "stategraph",
    "description": "Programmatic state-graph explorer with occasional LLM hypotheses",
    "agent_class": StateGraphAgent,
}

agents = [definition]

__all__ = ["definition", "agents"]
