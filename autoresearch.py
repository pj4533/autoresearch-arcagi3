"""
ARC-AGI-3 Autoresearch Orchestrator.

Two-phase loop:
1. RESEARCH: Analyze past experiments, propose next idea
2. EXECUTE: Implement changes, run benchmark, evaluate

Usage:
    # Start autoresearch loop (runs until interrupted)
    uv run python autoresearch.py --config qwen3.5-35b-local

    # Run with max experiments
    uv run python autoresearch.py --config qwen3.5-35b-local --max-experiments 5

    # Research only (propose ideas, don't execute)
    uv run python autoresearch.py --config qwen3.5-35b-local --research-only

    # Execute only (run queued experiments)
    uv run python autoresearch.py --config qwen3.5-35b-local --execute-only

    # Queue and run baseline experiments first
    uv run python autoresearch.py --config qwen3.5-35b-local --baselines
"""

import argparse
import logging
import sys

from arcagi3.autoresearch.experiment_db import ExperimentDB
from arcagi3.autoresearch.runner import ExperimentRunner
from arcagi3.autoresearch.researcher import Researcher
from arcagi3.autoresearch.executor import Executor

logger = logging.getLogger(__name__)


def autoresearch_loop(
    config: str,
    db_path: str = "experiments/experiments.db",
    max_experiments: int = None,
    max_actions: int = 100,
    research_only: bool = False,
    execute_only: bool = False,
):
    """Main autoresearch loop.

    Alternates between researcher (propose) and executor (implement + run).
    """
    db = ExperimentDB(db_path)
    runner = ExperimentRunner(db)

    experiment_count = 0

    while max_experiments is None or experiment_count < max_experiments:
        logger.info(f"\n{'='*60}")
        logger.info(f"Autoresearch cycle {experiment_count + 1}")
        logger.info(f"{'='*60}\n")

        if not execute_only:
            # Phase 1: Research — propose next experiment
            logger.info("Phase 1: RESEARCH — analyzing history, proposing next experiment...")
            researcher = Researcher(config, db)
            proposal = researcher.propose_next_experiment()

            if proposal is None:
                logger.info("Researcher has no more ideas. Stopping.")
                break

            logger.info(f"Proposed: {proposal.get('hypothesis', '?')}")
            logger.info(f"Category: {proposal.get('category', '?')}")
            logger.info(f"Changes: {proposal.get('changes', '?')[:100]}")

            if research_only:
                # Queue the experiment but don't run it
                exp_id = db.create_experiment(
                    agent="explorer",
                    config=config,
                    game_ids=proposal.get("games", ["ls20", "ft09", "vc33"]),
                    hypothesis=proposal.get("hypothesis", ""),
                    changes=proposal.get("changes", ""),
                )
                logger.info(f"Queued experiment {exp_id} (research-only mode)")
                experiment_count += 1
                continue

        if not research_only:
            if execute_only:
                # Run pending experiments from the queue
                pending = db.get_pending()
                if not pending:
                    logger.info("No pending experiments. Stopping.")
                    break
                result = runner.run_experiment(
                    pending[0]["id"], max_actions=max_actions
                )
            else:
                # Phase 2: Execute — implement and run
                logger.info("\nPhase 2: EXECUTE — implementing changes, running benchmark...")
                executor = Executor(config, db, runner, max_actions=max_actions)
                result = executor.run_experiment(proposal)

            verdict = result.get("verdict", "?")
            score = result.get("avg_score", "?")
            logger.info(f"\nResult: {result.get('id', '?')} [{verdict}] score={score}")

            # Update researcher's knowledge
            if not execute_only:
                researcher.update_from_result(result)

        experiment_count += 1

    logger.info(f"\nAutoresearch complete. Ran {experiment_count} experiments.")
    summary = db.get_summary()
    logger.info(f"Total: {summary['total']}, Accepted: {summary['accepted']}")
    if summary["best_experiment"]:
        best = summary["best_experiment"]
        logger.info(f"Best: {best['id']} (score: {best['avg_score']:.4f})")


def main():
    parser = argparse.ArgumentParser(
        description="ARC-AGI-3 Autoresearch Orchestrator"
    )
    parser.add_argument(
        "--config",
        default="qwen3.5-35b-local",
        help="Model config for both researcher and executor (default: qwen3.5-35b-local)",
    )
    parser.add_argument(
        "--max-experiments",
        type=int,
        default=None,
        help="Max experiments to run (default: unlimited)",
    )
    parser.add_argument(
        "--max-actions",
        type=int,
        default=100,
        help="Max actions per game (default: 100)",
    )
    parser.add_argument(
        "--baselines",
        action="store_true",
        help="Queue and run baseline experiments first",
    )
    parser.add_argument(
        "--research-only",
        action="store_true",
        help="Only propose ideas, don't execute",
    )
    parser.add_argument(
        "--execute-only",
        action="store_true",
        help="Only run pending experiments, don't propose new ones",
    )
    parser.add_argument(
        "--db",
        default="experiments/experiments.db",
        help="Path to experiment database",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.baselines:
        logger.info("Queueing baseline experiments...")
        db = ExperimentDB(args.db)
        runner = ExperimentRunner(db)
        runner.queue_baselines()
        if not args.execute_only and not args.research_only:
            logger.info("Running baselines before starting autoresearch loop...")
            runner.run_pending(max_actions=args.max_actions)

    try:
        autoresearch_loop(
            config=args.config,
            db_path=args.db,
            max_experiments=args.max_experiments,
            max_actions=args.max_actions,
            research_only=args.research_only,
            execute_only=args.execute_only,
        )
    except KeyboardInterrupt:
        logger.info("\nAutoresearch interrupted. Progress saved to DB.")
        sys.exit(0)


if __name__ == "__main__":
    main()
