"""
SQLite-backed experiment tracker for ARC-AGI-3 autoresearch.

Stores experiment metadata, results, and per-game metrics for querying
by the batch runner, dashboard, and researcher agent.
"""

import hashlib
import json
import logging
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    agent TEXT NOT NULL,
    config TEXT NOT NULL,
    game_ids TEXT NOT NULL,
    hypothesis TEXT,
    changes TEXT,
    total_score REAL,
    avg_score REAL,
    total_actions INTEGER,
    total_cost REAL,
    per_game_results TEXT,
    verdict TEXT,
    notes TEXT,
    duration_seconds REAL,
    parent_experiment_id TEXT,
    git_commit TEXT,
    prompt_hash TEXT
);

CREATE TABLE IF NOT EXISTS experiment_metrics (
    experiment_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    score REAL,
    actions_taken INTEGER,
    levels_completed INTEGER,
    cost REAL,
    duration_seconds REAL,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);
"""


class ExperimentDB:
    """SQLite experiment tracker."""

    def __init__(self, db_path: str = "experiments/experiments.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _next_id(self) -> str:
        """Generate next experiment ID (exp_001, exp_002, ...)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM experiments ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return "exp_001"
        last_num = int(row["id"].split("_")[1])
        return f"exp_{last_num + 1:03d}"

    def create_experiment(
        self,
        agent: str,
        config: str,
        game_ids: List[str],
        hypothesis: str = "",
        changes: str = "",
        parent_experiment_id: Optional[str] = None,
    ) -> str:
        """Create a new pending experiment and return its ID."""
        exp_id = self._next_id()
        now = datetime.now(timezone.utc).isoformat()
        git_commit = self._get_git_commit()
        prompt_hash = self._get_prompt_hash()

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO experiments
                   (id, timestamp, status, agent, config, game_ids,
                    hypothesis, changes, parent_experiment_id, git_commit, prompt_hash)
                   VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    exp_id,
                    now,
                    agent,
                    config,
                    ",".join(game_ids),
                    hypothesis,
                    changes,
                    parent_experiment_id,
                    git_commit,
                    prompt_hash,
                ),
            )
        logger.info(f"Created experiment {exp_id}: {hypothesis}")
        return exp_id

    def update_experiment(self, exp_id: str, **kwargs) -> None:
        """Update experiment fields."""
        if not kwargs:
            return
        fields = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [exp_id]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE experiments SET {fields} WHERE id = ?", values
            )

    def get_experiment(self, exp_id: str) -> Optional[Dict[str, Any]]:
        """Get a single experiment by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM experiments WHERE id = ?", (exp_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_experiments(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        order_by: str = "timestamp DESC",
    ) -> List[Dict[str, Any]]:
        """List experiments, optionally filtered by status."""
        query = "SELECT * FROM experiments"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += f" ORDER BY {order_by} LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_pending(self) -> List[Dict[str, Any]]:
        """Get all pending experiments in creation order."""
        return self.list_experiments(status="pending", order_by="id ASC")

    def get_best(self, top: int = 10) -> List[Dict[str, Any]]:
        """Get top experiments by average score."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM experiments
                   WHERE status = 'completed' AND avg_score IS NOT NULL
                   ORDER BY avg_score DESC LIMIT ?""",
                (top,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_metric(
        self,
        experiment_id: str,
        game_id: str,
        score: float = 0.0,
        actions_taken: int = 0,
        levels_completed: int = 0,
        cost: float = 0.0,
        duration_seconds: float = 0.0,
    ) -> None:
        """Add a per-game metric for an experiment."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO experiment_metrics
                   (experiment_id, game_id, score, actions_taken,
                    levels_completed, cost, duration_seconds)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    experiment_id,
                    game_id,
                    score,
                    actions_taken,
                    levels_completed,
                    cost,
                    duration_seconds,
                ),
            )

    def get_metrics(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Get per-game metrics for an experiment."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM experiment_metrics WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics across all experiments."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM experiments WHERE status = 'completed'"
            ).fetchone()[0]
            accepted = conn.execute(
                "SELECT COUNT(*) FROM experiments WHERE verdict = 'accept'"
            ).fetchone()[0]
            best_row = conn.execute(
                """SELECT id, avg_score FROM experiments
                   WHERE status = 'completed' AND avg_score IS NOT NULL
                   ORDER BY avg_score DESC LIMIT 1"""
            ).fetchone()
        return {
            "total": total,
            "completed": completed,
            "accepted": accepted,
            "pending": total - completed,
            "best_experiment": dict(best_row) if best_row else None,
        }

    @staticmethod
    def _get_git_commit() -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    @staticmethod
    def _get_prompt_hash() -> Optional[str]:
        """Hash all prompt template files for quick comparison."""
        prompt_dirs = [
            "src/arcagi3/explorer_agent/prompts",
            "src/arcagi3/adcr_agent/prompts",
        ]
        hasher = hashlib.sha256()
        for prompt_dir in prompt_dirs:
            prompt_path = Path(prompt_dir)
            if not prompt_path.exists():
                continue
            for f in sorted(prompt_path.glob("*.prompt")):
                hasher.update(f.read_bytes())
        return hasher.hexdigest()[:12]
