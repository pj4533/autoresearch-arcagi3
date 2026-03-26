"""
CLI for managing the ARC-AGI-3 experiment queue.

Usage:
    uv run python -m arcagi3.autoresearch.queue add --hypothesis "..." --games ls20,ft09,vc33 --config qwen3.5-35b-local
    uv run python -m arcagi3.autoresearch.queue list
    uv run python -m arcagi3.autoresearch.queue show exp_005
    uv run python -m arcagi3.autoresearch.queue best --top 10
"""

import argparse
import json
import sys

from arcagi3.autoresearch.experiment_db import ExperimentDB

DEFAULT_GAMES = "ls20,ft09,vc33"
DEFAULT_CONFIG = "qwen3.5-35b-local"
DEFAULT_AGENT = "explorer"


def cmd_add(db: ExperimentDB, args):
    """Add a new experiment to the queue."""
    game_ids = [g.strip() for g in args.games.split(",")]
    exp_id = db.create_experiment(
        agent=args.agent,
        config=args.config,
        game_ids=game_ids,
        hypothesis=args.hypothesis,
        changes=args.changes or "",
        parent_experiment_id=args.parent,
    )
    print(f"Created experiment: {exp_id}")


def cmd_list(db: ExperimentDB, args):
    """List experiments."""
    experiments = db.list_experiments(status=args.status, limit=args.limit)
    if not experiments:
        print("No experiments found.")
        return

    # Header
    print(f"{'ID':<10} {'Status':<12} {'Agent':<10} {'Config':<25} {'Score':<8} {'Verdict':<10} {'Hypothesis'}")
    print("-" * 120)

    for exp in experiments:
        score = f"{exp['avg_score']:.4f}" if exp.get("avg_score") is not None else "-"
        verdict = exp.get("verdict") or "-"
        hypothesis = (exp.get("hypothesis") or "")[:50]
        print(
            f"{exp['id']:<10} {exp['status']:<12} {exp['agent']:<10} "
            f"{exp['config']:<25} {score:<8} {verdict:<10} {hypothesis}"
        )


def cmd_show(db: ExperimentDB, args):
    """Show detailed experiment info."""
    exp = db.get_experiment(args.experiment_id)
    if not exp:
        print(f"Experiment {args.experiment_id} not found.")
        sys.exit(1)

    print(f"Experiment: {exp['id']}")
    print(f"  Status:     {exp['status']}")
    print(f"  Agent:      {exp['agent']}")
    print(f"  Config:     {exp['config']}")
    print(f"  Games:      {exp['game_ids']}")
    print(f"  Hypothesis: {exp['hypothesis']}")
    print(f"  Changes:    {exp['changes']}")
    print(f"  Verdict:    {exp.get('verdict') or '-'}")
    print(f"  Score:      {exp.get('avg_score') or '-'}")
    print(f"  Actions:    {exp.get('total_actions') or '-'}")
    print(f"  Cost:       ${exp.get('total_cost') or 0:.4f}")
    print(f"  Duration:   {exp.get('duration_seconds') or 0:.1f}s")
    print(f"  Parent:     {exp.get('parent_experiment_id') or '-'}")
    print(f"  Git:        {exp.get('git_commit') or '-'}")
    print(f"  Prompts:    {exp.get('prompt_hash') or '-'}")
    print(f"  Timestamp:  {exp['timestamp']}")

    if exp.get("per_game_results"):
        print("\n  Per-game results:")
        results = json.loads(exp["per_game_results"])
        for game_id, r in results.items():
            error = f" ERROR: {r['error']}" if r.get("error") else ""
            print(
                f"    {game_id}: score={r.get('score', 0)}, "
                f"actions={r.get('actions', 0)}, "
                f"cost=${r.get('cost', 0):.4f}{error}"
            )

    metrics = db.get_metrics(exp["id"])
    if metrics:
        print("\n  Metrics:")
        for m in metrics:
            print(
                f"    {m['game_id']}: score={m['score']}, "
                f"actions={m['actions_taken']}, "
                f"levels={m.get('levels_completed', 0)}"
            )


def cmd_best(db: ExperimentDB, args):
    """Show top experiments by score."""
    best = db.get_best(top=args.top)
    if not best:
        print("No completed experiments yet.")
        return

    print(f"Top {len(best)} experiments by average score:\n")
    print(f"{'Rank':<6} {'ID':<10} {'Score':<10} {'Actions':<10} {'Verdict':<10} {'Hypothesis'}")
    print("-" * 100)

    for i, exp in enumerate(best, 1):
        hypothesis = (exp.get("hypothesis") or "")[:45]
        print(
            f"{i:<6} {exp['id']:<10} {exp['avg_score']:<10.4f} "
            f"{exp.get('total_actions', 0):<10} "
            f"{exp.get('verdict') or '-':<10} {hypothesis}"
        )


def cmd_summary(db: ExperimentDB, args):
    """Show experiment summary."""
    summary = db.get_summary()
    print("Experiment Summary:")
    print(f"  Total:     {summary['total']}")
    print(f"  Completed: {summary['completed']}")
    print(f"  Accepted:  {summary['accepted']}")
    print(f"  Pending:   {summary['pending']}")
    if summary["best_experiment"]:
        best = summary["best_experiment"]
        print(f"  Best:      {best['id']} (score: {best['avg_score']:.4f})")


def main():
    parser = argparse.ArgumentParser(
        prog="arcagi3.autoresearch.queue",
        description="Manage the ARC-AGI-3 experiment queue",
    )
    parser.add_argument("--db", default="experiments/experiments.db", help="DB path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_parser = subparsers.add_parser("add", help="Add experiment to queue")
    add_parser.add_argument("--hypothesis", required=True, help="What we're testing")
    add_parser.add_argument("--changes", help="Description of changes")
    add_parser.add_argument("--games", default=DEFAULT_GAMES, help="Comma-separated game IDs")
    add_parser.add_argument("--config", default=DEFAULT_CONFIG, help="Model config name")
    add_parser.add_argument("--agent", default=DEFAULT_AGENT, help="Agent name")
    add_parser.add_argument("--parent", help="Parent experiment ID")

    # list
    list_parser = subparsers.add_parser("list", help="List experiments")
    list_parser.add_argument("--status", help="Filter by status (pending/running/completed/failed)")
    list_parser.add_argument("--limit", type=int, default=50, help="Max results")

    # show
    show_parser = subparsers.add_parser("show", help="Show experiment details")
    show_parser.add_argument("experiment_id", help="Experiment ID")

    # best
    best_parser = subparsers.add_parser("best", help="Show top experiments")
    best_parser.add_argument("--top", type=int, default=10, help="Number of results")

    # summary
    subparsers.add_parser("summary", help="Show experiment summary")

    args = parser.parse_args()
    db = ExperimentDB(args.db)

    commands = {
        "add": cmd_add,
        "list": cmd_list,
        "show": cmd_show,
        "best": cmd_best,
        "summary": cmd_summary,
    }
    commands[args.command](db, args)


if __name__ == "__main__":
    main()
