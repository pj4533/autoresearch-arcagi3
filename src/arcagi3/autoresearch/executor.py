"""
Executor agent for ARC-AGI-3 autoresearch.

Takes a proposed experiment, creates a git branch, applies changes
via LLM, runs the benchmark, and evaluates results.
"""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from arcagi3.autoresearch.experiment_db import ExperimentDB
from arcagi3.autoresearch.runner import ExperimentRunner

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM_PROMPT = """You are a code modification assistant. You receive a description of changes
to make to an ARC-AGI-3 game-playing agent, and you produce the exact file modifications needed.

For each file that needs changing, output a JSON array of modifications:

{
    "modifications": [
        {
            "file": "path/to/file.py",
            "action": "replace",
            "old": "exact text to find",
            "new": "replacement text"
        },
        {
            "file": "path/to/file.prompt",
            "action": "rewrite",
            "content": "complete new file content"
        }
    ]
}

Rules:
- For "replace" actions: "old" must be an EXACT substring of the current file content
- For "rewrite" actions: provide the COMPLETE new file content
- Use "replace" for surgical changes, "rewrite" for complete prompt overhauls
- Preserve existing imports, class structure, and method signatures
- Keep the agent's step() method signature: step(self, context: SessionContext) -> GameStep
- Do NOT change the MultimodalAgent base class or its interface
- Python code must be syntactically valid
"""


class Executor:
    """Applies proposed changes, runs experiments, and evaluates results."""

    def __init__(
        self,
        config: str,
        db: ExperimentDB,
        runner: ExperimentRunner,
        max_actions: int = 100,
    ):
        self.config = config
        self.db = db
        self.runner = runner
        self.max_actions = max_actions

    def run_experiment(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a full experiment from proposal to verdict.

        Steps:
        1. Create experiment in DB
        2. Create git branch
        3. Apply code changes via LLM
        4. Run benchmark
        5. Evaluate and set verdict
        6. Return to main branch
        """
        hypothesis = proposal.get("hypothesis", "Unknown")
        changes_desc = proposal.get("changes", "")
        category = proposal.get("category", "unknown")
        games = proposal.get("games", ["ls20", "ft09", "vc33"])

        # Find parent (most recent accepted or baseline)
        parent_id = self._find_parent_experiment()

        # Create experiment record
        exp_id = self.db.create_experiment(
            agent="explorer",
            config=self.config,
            game_ids=games,
            hypothesis=hypothesis,
            changes=changes_desc,
            parent_experiment_id=parent_id,
        )

        branch_name = self._make_branch_name(exp_id, hypothesis)
        logger.info(f"Executor starting experiment {exp_id} on branch {branch_name}")

        try:
            # Create branch
            self._git("checkout", "-b", branch_name)

            # Apply changes
            success = self._apply_changes(proposal)
            if not success:
                self.db.update_experiment(
                    exp_id, status="failed", notes="Failed to apply code changes"
                )
                self._git("checkout", "main")
                return self.db.get_experiment(exp_id)

            # Commit changes
            self._git("add", "-A")
            self._git("commit", "-m", f"exp: {exp_id} - {hypothesis[:60]}")

            # Run the experiment
            result = self.runner.run_experiment(
                exp_id, max_actions=self.max_actions
            )

            return result

        except Exception as e:
            logger.error(f"Experiment {exp_id} failed: {e}")
            self.db.update_experiment(
                exp_id, status="failed", notes=str(e)
            )
            return self.db.get_experiment(exp_id)

        finally:
            # Always return to main
            self._git("checkout", "main")

    def _apply_changes(self, proposal: Dict[str, Any]) -> bool:
        """Apply code modifications using LLM to generate exact changes."""
        from arcagi3.adapters import create_provider
        from arcagi3.utils.parsing import extract_json_from_response

        changes_desc = proposal.get("changes", "")
        category = proposal.get("category", "")

        # Read current file contents for context
        from arcagi3.autoresearch.mutations import MUTATION_CATEGORIES

        targets = MUTATION_CATEGORIES.get(category, {}).get("targets", [])
        file_contents = {}
        for target in targets:
            path = Path(target)
            if path.exists():
                file_contents[target] = path.read_text()

        # Build LLM prompt for code modifications
        prompt_parts = [
            f"## Change Request\n{changes_desc}\n",
            f"## Category: {category}\n",
        ]
        for filepath, content in file_contents.items():
            prompt_parts.append(
                f"## Current content of {filepath}\n```\n{content}\n```\n"
            )
        prompt_parts.append(
            "Generate the exact modifications needed. "
            "Output JSON with the modifications array."
        )

        messages = [
            {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(prompt_parts)},
        ]

        provider = create_provider(self.config)
        response = provider.call_provider(messages)
        response_text = provider.extract_content(response)

        try:
            result = extract_json_from_response(response_text)
            modifications = result.get("modifications", [])
        except ValueError as e:
            logger.error(f"Failed to parse executor response: {e}")
            return False

        if not modifications:
            logger.warning("Executor produced no modifications.")
            return False

        # Apply each modification
        for mod in modifications:
            filepath = mod.get("file", "")
            action = mod.get("action", "")

            if not filepath:
                continue

            path = Path(filepath)

            try:
                if action == "rewrite":
                    content = mod.get("content", "")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
                    logger.info(f"Rewrote {filepath}")

                elif action == "replace":
                    old = mod.get("old", "")
                    new = mod.get("new", "")
                    if not path.exists():
                        logger.warning(f"File not found: {filepath}")
                        continue
                    current = path.read_text()
                    if old not in current:
                        logger.warning(
                            f"Old text not found in {filepath}. Skipping."
                        )
                        continue
                    updated = current.replace(old, new, 1)
                    path.write_text(updated)
                    logger.info(f"Applied replacement in {filepath}")

            except Exception as e:
                logger.error(f"Failed to modify {filepath}: {e}")
                return False

        # Validate Python files are syntactically correct
        for mod in modifications:
            filepath = mod.get("file", "")
            if filepath.endswith(".py"):
                try:
                    compile(Path(filepath).read_text(), filepath, "exec")
                except SyntaxError as e:
                    logger.error(f"Syntax error in {filepath}: {e}")
                    return False

        return True

    def _find_parent_experiment(self) -> Optional[str]:
        """Find the most recent accepted experiment, or latest baseline."""
        accepted = self.db.list_experiments(limit=1, order_by="id DESC")
        for exp in self.db.list_experiments(limit=50, order_by="id DESC"):
            if exp.get("verdict") == "accept":
                return exp["id"]
        # Fall back to latest completed baseline
        for exp in self.db.list_experiments(limit=50, order_by="id DESC"):
            if exp.get("verdict") == "baseline" and exp.get("status") == "completed":
                return exp["id"]
        return None

    def _make_branch_name(self, exp_id: str, hypothesis: str) -> str:
        """Create a git branch name from experiment ID and hypothesis."""
        # Clean hypothesis into a slug
        slug = re.sub(r"[^a-z0-9]+", "_", hypothesis.lower().strip())[:40]
        slug = slug.strip("_")
        return f"exp/{exp_id}_{slug}"

    def _git(self, *args) -> str:
        """Run a git command and return stdout."""
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning(f"git {' '.join(args)}: {result.stderr.strip()}")
        return result.stdout.strip()
