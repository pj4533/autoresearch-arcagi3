"""
Researcher agent for ARC-AGI-3 autoresearch.

Analyzes experiment history and current agent code to propose
the next experiment. Uses an LLM call to generate ideas.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from arcagi3.autoresearch.experiment_db import ExperimentDB
from arcagi3.autoresearch.mutations import MUTATION_CATEGORIES, TIER_ORDER, get_mutation_summary

logger = logging.getLogger(__name__)

RESEARCHER_SYSTEM_PROMPT = """You are an AI research assistant specializing in ARC-AGI-3 game-playing agent optimization.

Your job: analyze past experiment results and propose the NEXT experiment to run.

ARC-AGI-3 games are interactive 64x64 grid environments where an agent takes actions
(move up/down/left/right, perform, click, undo) to solve levels. The metric is action
efficiency vs human baseline: fewer actions = better score.

The agent you're improving uses a Probe -> Explore -> Exploit architecture:
- PROBE: Systematically try each action once (zero LLM cost) to map action effects
- EXPLORE: Use LLM to analyze frames, form hypotheses, choose actions
- EXPLOIT: (not yet implemented) Execute confident plans efficiently

You must propose ONE specific, testable change. Be concrete — specify exact prompt
modifications, code changes, or parameter tweaks. Small, focused changes are better
than sweeping rewrites.

Respond with this exact JSON format:
{
    "hypothesis": "What we expect to improve and why",
    "category": "One of the mutation categories",
    "changes": "Exact description of what to modify (specific enough for another AI to implement)",
    "games": ["ls20", "ft09", "vc33"],
    "expected_impact": "What metric should improve and by roughly how much",
    "priority": "high/medium/low"
}
"""


class Researcher:
    """LLM-driven research idea generator."""

    def __init__(self, config: str, db: ExperimentDB):
        self.config = config
        self.db = db

    def propose_next_experiment(self) -> Optional[Dict[str, Any]]:
        """Analyze history and propose the next experiment.

        Returns a proposal dict or None if no ideas remain.
        """
        from arcagi3.adapters import create_provider
        from arcagi3.utils.parsing import extract_json_from_response

        provider = create_provider(self.config)

        # Build the research prompt
        prompt = self._build_prompt()

        messages = [
            {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        logger.info("Researcher generating next experiment proposal...")

        response = provider.call_provider(messages)
        response_text = provider.extract_content(response)

        try:
            proposal = extract_json_from_response(response_text)
            logger.info(f"Researcher proposed: {proposal.get('hypothesis', '?')}")
            self._update_ideas_file(proposal)
            return proposal
        except ValueError as e:
            logger.error(f"Failed to parse researcher response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            return None

    def _build_prompt(self) -> str:
        """Build the research prompt with experiment history and current code."""
        parts = []

        # Experiment history
        experiments = self.db.list_experiments(limit=20, order_by="id DESC")
        if experiments:
            parts.append("## Recent Experiment History (newest first)\n")
            for exp in experiments:
                parts.append(
                    f"- {exp['id']}: [{exp['status']}] {exp.get('verdict', '?')} | "
                    f"score={exp.get('avg_score', '?')} | actions={exp.get('total_actions', '?')} | "
                    f"{exp.get('hypothesis', '?')}"
                )
            parts.append("")
        else:
            parts.append("## No experiments have been run yet. Propose a baseline or first experiment.\n")

        # Best experiments
        best = self.db.get_best(top=5)
        if best:
            parts.append("## Best Experiments So Far\n")
            for exp in best:
                parts.append(
                    f"- {exp['id']}: score={exp['avg_score']:.4f} | "
                    f"{exp.get('hypothesis', '?')}"
                )
            parts.append("")

        # Current agent code (key sections)
        parts.append("## Current Explorer Agent Code\n")
        agent_code = self._read_file("src/arcagi3/explorer_agent/agent.py")
        if agent_code:
            parts.append(f"```python\n{agent_code}\n```\n")

        # Current prompts
        parts.append("## Current Prompt Templates\n")
        for prompt_name in ["system", "explore", "convert"]:
            content = self._read_file(f"src/arcagi3/explorer_agent/prompts/{prompt_name}.prompt")
            if content:
                parts.append(f"### {prompt_name}.prompt\n```\n{content}\n```\n")

        # Available mutation categories
        parts.append("## Available Mutation Categories\n")
        parts.append(get_mutation_summary())
        parts.append("")

        # Instructions
        parts.append(
            "## Your Task\n"
            "Based on the experiment history (or lack thereof), current code, and available "
            "mutation categories, propose the SINGLE most impactful experiment to run next.\n"
            "If no experiments exist yet, propose a baseline or low-hanging-fruit change.\n"
            "If recent experiments show a pattern (e.g., scores stuck at 0), "
            "pivot to a different category.\n"
            "NEVER propose a change identical to a previous experiment.\n"
        )

        return "\n".join(parts)

    def _read_file(self, path: str) -> Optional[str]:
        """Read a file relative to the repo root."""
        try:
            return Path(path).read_text()
        except FileNotFoundError:
            return None

    def _update_ideas_file(self, proposal: Dict[str, Any]) -> None:
        """Append the proposal to the ideas tracking file."""
        ideas_path = Path("experiments/ideas.md")
        ideas_path.parent.mkdir(parents=True, exist_ok=True)

        entry = (
            f"\n- [ ] **{proposal.get('category', '?')}**: {proposal.get('hypothesis', '?')}\n"
            f"  - Changes: {proposal.get('changes', '?')}\n"
            f"  - Expected: {proposal.get('expected_impact', '?')}\n"
            f"  - Priority: {proposal.get('priority', '?')}\n"
        )

        if not ideas_path.exists():
            ideas_path.write_text("# Research Ideas (Auto-maintained)\n" + entry)
        else:
            with open(ideas_path, "a") as f:
                f.write(entry)

    def update_from_result(self, result: Dict[str, Any]) -> None:
        """Update ideas file with experiment outcome."""
        ideas_path = Path("experiments/ideas.md")
        if not ideas_path.exists():
            return

        exp_id = result.get("id", "?")
        verdict = result.get("verdict", "?")
        score = result.get("avg_score", "?")
        hypothesis = result.get("hypothesis", "?")

        with open(ideas_path, "a") as f:
            f.write(
                f"\n### Result: {exp_id} [{verdict}] score={score}\n"
                f"  {hypothesis}\n"
            )
