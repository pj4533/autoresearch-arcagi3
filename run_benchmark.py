"""
Run ARC-AGI-3 benchmark: play games and print a clean summary.

Usage:
    uv run python run_benchmark.py
    uv run python run_benchmark.py --config qwen3.5-35b-local --max-actions 40
    uv run python run_benchmark.py --games ls20  # single game for quick screen
    uv run python run_benchmark.py --agent adcr --games ls20,ft09,vc33
"""

import argparse
import logging
import time

from dotenv import load_dotenv

load_dotenv()

DEFAULT_GAMES = ["ls20", "ft09", "vc33"]
DEFAULT_CONFIG = "qwen3.5-35b-local"
DEFAULT_MAX_ACTIONS = 40


def resolve_agent(agent_name: str):
    """Resolve agent class from name."""
    if agent_name == "explorer":
        from arcagi3.explorer_agent import ExplorerAgent
        return ExplorerAgent
    elif agent_name == "adcr":
        from arcagi3.adcr_agent import ADCRAgent
        return ADCRAgent
    else:
        raise ValueError(f"Unknown agent: {agent_name}")


def run_benchmark(agent_name: str, config: str, games: list[str], max_actions: int) -> dict:
    """Run benchmark across specified games, return results dict."""
    from arcagi3.arc3tester import ARC3Tester

    agent_class = resolve_agent(agent_name)

    results = {}
    total_score = 0.0
    total_actions = 0
    total_duration = 0.0

    for game_id in games:
        print(f"Running {game_id}...", flush=True)
        start = time.time()

        try:
            tester = ARC3Tester(
                config=config,
                save_results_dir=f"results/benchmark/{game_id}",
                max_actions=max_actions,
                num_plays=0,
                use_vision=False,
                submit_scorecard=False,
                agent_class=agent_class,
            )

            result = tester.play_game(game_id)
            game_score = result.final_score
            game_actions = result.actions_taken
            game_duration = result.duration_seconds

        except Exception as e:
            logging.error(f"Game {game_id} failed: {e}")
            game_score = 0
            game_actions = 0
            game_duration = time.time() - start

        results[game_id] = {
            "score": game_score,
            "actions": game_actions,
            "duration": round(game_duration, 1),
        }
        total_score += game_score
        total_actions += game_actions
        total_duration += game_duration

    num_games = len(games)
    avg_score = total_score / num_games if num_games > 0 else 0.0

    summary = {
        "games": results,
        "avg_score": avg_score,
        "total_actions": total_actions,
        "total_duration": round(total_duration, 1),
    }
    return summary


def print_summary(summary: dict):
    """Print clean benchmark summary to stdout."""
    print()
    print("=== Benchmark Results ===")
    for game_id, r in summary["games"].items():
        print(f"{game_id}: score={r['score']}  actions={r['actions']}  duration={r['duration']}s")
    print("---")
    print(f"Average Score: {summary['avg_score']:.4f}")
    print(f"Total Actions: {summary['total_actions']}")
    print(f"Total Duration: {summary['total_duration']}s")


def main():
    parser = argparse.ArgumentParser(description="Run ARC-AGI-3 benchmark")
    parser.add_argument("--agent", default="explorer", help="Agent name (default: explorer)")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Model config (default: {DEFAULT_CONFIG})")
    parser.add_argument("--games", default=",".join(DEFAULT_GAMES), help="Comma-separated game IDs")
    parser.add_argument("--max-actions", type=int, default=DEFAULT_MAX_ACTIONS, help="Max actions per game")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    games = [g.strip() for g in args.games.split(",")]
    summary = run_benchmark(args.agent, args.config, games, args.max_actions)
    print_summary(summary)


if __name__ == "__main__":
    main()
