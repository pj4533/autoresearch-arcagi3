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
import os
import time

from dotenv import load_dotenv

load_dotenv()

DEFAULT_GAMES = [
    "ar25-e3c63847", "bp35-0a0ad940", "cd82-fb555c5d", "cn04-65d47d14",
    "dc22-4c9bff3e", "ft09-0d8bbf25", "g50t-5849a774", "ka59-9f096b4a",
    "lf52-271a04aa", "lp85-305b61c3", "ls20-9607627b", "m0r0-dadda488",
    "r11l-aa269680", "re86-4e57566e", "s5i5-a48e4b1d", "sb26-7fbdac44",
    "sc25-f9b21a2f", "sk48-41055498", "sp80-0ee2d095", "su15-4c352900",
    "tn36-ab4f63cc", "tr87-cd924810", "tu93-2b534c15", "vc33-9851e02b",
    "wa30-ee6fef47",
]
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
    elif agent_name == "stategraph":
        from arcagi3.stategraph_agent import StateGraphAgent
        return StateGraphAgent
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
                submit_scorecard=True,
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
