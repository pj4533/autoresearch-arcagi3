"""
Batch experiment runner for ARC-AGI-3 autoresearch.

Reads experiments from the SQLite queue and runs them sequentially
using the existing ARC3Tester infrastructure in offline mode.

Usage:
    # Run all pending experiments
    uv run python -m arcagi3.autoresearch.runner

    # Run a specific experiment
    uv run python -m arcagi3.autoresearch.runner --experiment exp_005

    # Run continuously until queue is empty
    uv run python -m arcagi3.autoresearch.runner --continuous

    # Resume failed experiments
    uv run python -m arcagi3.autoresearch.runner --resume

    # Queue and run baseline experiments
    uv run python -m arcagi3.autoresearch.runner --baselines
"""

import argparse
import json
import logging
import time
from typing import Dict, List, Optional

from arcagi3.autoresearch.experiment_db import ExperimentDB

logger = logging.getLogger(__name__)

# Default games and configs for baseline experiments
DEFAULT_GAMES = ["ls20", "ft09", "vc33"]

BASELINE_EXPERIMENTS = [
    {
        "agent": "explorer",
        "config": "qwen3.5-35b-local",
        "hypothesis": "Baseline: Explorer agent + Qwen3.5-35B MoE (fast, primary model)",
    },
    {
        "agent": "explorer",
        "config": "qwen3-32b-local",
        "hypothesis": "Baseline: Explorer agent + Qwen3-32B dense (higher quality per-token)",
    },
    {
        "agent": "adcr",
        "config": "qwen3.5-35b-local",
        "hypothesis": "Baseline: ADCR agent + Qwen3.5-35B MoE (reference agent comparison)",
    },
    {
        "agent": "explorer",
        "config": "qwq-32b-local",
        "hypothesis": "Baseline: Explorer agent + QwQ-32B reasoning (deep chain-of-thought)",
    },
]


class ExperimentRunner:
    """Runs queued experiments using ARC3Tester in offline mode."""

    def __init__(self, db: ExperimentDB):
        self.db = db

    def run_experiment(
        self,
        exp_id: str,
        max_actions: int = 100,
        save_results_dir: Optional[str] = None,
    ) -> Dict:
        """Run a single experiment by ID.

        Returns the updated experiment dict from the DB.
        """
        from arcagi3.arc3tester import ARC3Tester

        exp = self.db.get_experiment(exp_id)
        if not exp:
            raise ValueError(f"Experiment {exp_id} not found")

        logger.info(f"=== Running experiment {exp_id}: {exp['hypothesis']} ===")
        self.db.update_experiment(exp_id, status="running")

        game_ids = exp["game_ids"].split(",")
        agent_name = exp["agent"]
        config = exp["config"]

        # Resolve agent class from registry
        agent_class, agent_kwargs_fn = self._resolve_agent(agent_name)

        start_time = time.time()
        per_game_results = {}
        total_score = 0.0
        total_actions = 0
        total_cost = 0.0

        for game_id in game_ids:
            game_id = game_id.strip()
            logger.info(f"  Running game {game_id} with agent={agent_name}, config={config}")

            try:
                tester = ARC3Tester(
                    config=config,
                    save_results_dir=save_results_dir or f"results/autoresearch/{exp_id}",
                    max_actions=max_actions,
                    num_plays=0,  # infinite plays within action budget
                    use_vision=False,  # MLX models are text-only
                    submit_scorecard=False,  # offline mode
                    agent_class=agent_class,
                    agent_kwargs=agent_kwargs_fn() if agent_kwargs_fn else None,
                )

                result = tester.play_game(game_id)

                game_score = result.final_score
                game_actions = result.actions_taken
                game_cost = result.total_cost.total_cost if result.total_cost else 0.0
                game_duration = result.duration_seconds

                per_game_results[game_id] = {
                    "score": game_score,
                    "actions": game_actions,
                    "cost": game_cost,
                    "duration": game_duration,
                    "state": result.final_state,
                }

                self.db.add_metric(
                    experiment_id=exp_id,
                    game_id=game_id,
                    score=game_score,
                    actions_taken=game_actions,
                    cost=game_cost,
                    duration_seconds=game_duration,
                )

                total_score += game_score
                total_actions += game_actions
                total_cost += game_cost

                logger.info(
                    f"  Game {game_id}: score={game_score}, "
                    f"actions={game_actions}, cost=${game_cost:.4f}"
                )

            except Exception as e:
                logger.error(f"  Game {game_id} failed: {e}")
                per_game_results[game_id] = {
                    "score": 0,
                    "actions": 0,
                    "cost": 0,
                    "error": str(e),
                }

        duration = time.time() - start_time
        num_games = len(game_ids)
        avg_score = total_score / num_games if num_games > 0 else 0.0

        # Determine verdict
        verdict = self._determine_verdict(exp, avg_score)

        self.db.update_experiment(
            exp_id,
            status="completed",
            total_score=total_score,
            avg_score=avg_score,
            total_actions=total_actions,
            total_cost=total_cost,
            per_game_results=json.dumps(per_game_results),
            verdict=verdict,
            duration_seconds=duration,
        )

        logger.info(
            f"=== Experiment {exp_id} completed: "
            f"avg_score={avg_score:.4f}, verdict={verdict}, "
            f"duration={duration:.1f}s ==="
        )

        return self.db.get_experiment(exp_id)

    def run_pending(self, max_actions: int = 100) -> List[Dict]:
        """Run all pending experiments in order."""
        results = []
        pending = self.db.get_pending()

        if not pending:
            logger.info("No pending experiments in queue.")
            return results

        logger.info(f"Found {len(pending)} pending experiments.")

        for exp in pending:
            try:
                result = self.run_experiment(exp["id"], max_actions=max_actions)
                results.append(result)
            except KeyboardInterrupt:
                logger.info("Interrupted. Remaining experiments stay pending.")
                break
            except Exception as e:
                logger.error(f"Experiment {exp['id']} failed: {e}")
                self.db.update_experiment(
                    exp["id"], status="failed", notes=str(e)
                )

        return results

    def run_continuous(self, max_actions: int = 100, poll_interval: int = 60) -> None:
        """Run continuously, processing pending experiments until interrupted."""
        logger.info("Starting continuous experiment runner. Press Ctrl-C to stop.")
        try:
            while True:
                pending = self.db.get_pending()
                if pending:
                    self.run_pending(max_actions=max_actions)
                else:
                    logger.info(
                        f"Queue empty. Sleeping {poll_interval}s before next check..."
                    )
                    time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Continuous runner stopped.")

    def queue_baselines(self, games: Optional[List[str]] = None) -> List[str]:
        """Queue the standard baseline experiments."""
        games = games or DEFAULT_GAMES
        ids = []
        for baseline in BASELINE_EXPERIMENTS:
            exp_id = self.db.create_experiment(
                agent=baseline["agent"],
                config=baseline["config"],
                game_ids=games,
                hypothesis=baseline["hypothesis"],
                changes="baseline (no changes)",
            )
            ids.append(exp_id)
        logger.info(f"Queued {len(ids)} baseline experiments: {ids}")
        return ids

    def _resolve_agent(self, agent_name: str):
        """Resolve agent class and kwargs factory from name."""
        if agent_name == "explorer":
            from arcagi3.explorer_agent import ExplorerAgent

            return ExplorerAgent, None
        elif agent_name == "adcr":
            from arcagi3.adcr_agent import ADCRAgent

            return ADCRAgent, None
        else:
            raise ValueError(f"Unknown agent: {agent_name}")

    def _determine_verdict(self, exp: Dict, avg_score: float) -> str:
        """Determine experiment verdict by comparing to parent."""
        parent_id = exp.get("parent_experiment_id")
        if not parent_id:
            return "baseline"

        parent = self.db.get_experiment(parent_id)
        if not parent or parent.get("avg_score") is None:
            return "baseline"

        parent_score = parent["avg_score"]
        if avg_score > parent_score:
            return "accept"
        elif avg_score < parent_score:
            return "reject"
        else:
            return "neutral"


def main():
    parser = argparse.ArgumentParser(description="ARC-AGI-3 Experiment Runner")
    parser.add_argument("--experiment", type=str, help="Run a specific experiment ID")
    parser.add_argument("--continuous", action="store_true", help="Run continuously until stopped")
    parser.add_argument("--resume", action="store_true", help="Retry failed experiments")
    parser.add_argument("--baselines", action="store_true", help="Queue and run baseline experiments")
    parser.add_argument("--max-actions", type=int, default=100, help="Max actions per game")
    parser.add_argument("--db", type=str, default="experiments/experiments.db", help="DB path")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    db = ExperimentDB(args.db)
    runner = ExperimentRunner(db)

    if args.baselines:
        runner.queue_baselines()

    if args.resume:
        failed = db.list_experiments(status="failed")
        for exp in failed:
            db.update_experiment(exp["id"], status="pending")
        logger.info(f"Re-queued {len(failed)} failed experiments.")

    if args.experiment:
        runner.run_experiment(args.experiment, max_actions=args.max_actions)
    elif args.continuous:
        runner.run_continuous(max_actions=args.max_actions)
    else:
        runner.run_pending(max_actions=args.max_actions)


if __name__ == "__main__":
    main()
