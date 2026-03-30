"""Entry point for the ARC CLI tool."""
import argparse
import sys

from dotenv import load_dotenv


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="arc",
        description="ARC-AGI-3 CLI — play games from the command line",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list-games
    p_list = subparsers.add_parser("list-games", help="List available games")
    p_list.add_argument(
        "--backend", choices=["api", "local"], default="local",
        help="Game backend (default: local)",
    )

    # start
    p_start = subparsers.add_parser("start", help="Start a new game session")
    p_start.add_argument("game_id", help="Game identifier (e.g., ls20)")
    p_start.add_argument(
        "--backend", choices=["api", "local"], default="local",
        help="Game backend (default: local)",
    )
    p_start.add_argument(
        "--max-actions", type=int, default=40,
        help="Maximum actions allowed (default: 40)",
    )

    # action
    p_action = subparsers.add_parser("action", help="Take a game action")
    p_action.add_argument(
        "action_name",
        choices=["move_up", "move_down", "move_left", "move_right",
                 "perform", "click", "undo"],
        help="Action to take",
    )
    p_action.add_argument("--x", type=int, default=0, help="X coordinate for click")
    p_action.add_argument("--y", type=int, default=0, help="Y coordinate for click")
    p_action.add_argument("--image", action="store_true", help="Save frame as PNG")

    # state
    p_state = subparsers.add_parser("state", help="View current game state")
    p_state.add_argument("--image", action="store_true", help="Save frame as PNG")

    # end
    subparsers.add_parser("end", help="End the current session")

    # info
    subparsers.add_parser("info", help="Show session info")

    # scorecard (subcommand group)
    p_sc = subparsers.add_parser("scorecard", help="Multi-game scorecard operations")
    sc_sub = p_sc.add_subparsers(dest="sc_command", help="Scorecard commands")

    p_sc_open = sc_sub.add_parser("open", help="Open a new scorecard with all 25 games")
    p_sc_open.add_argument("--max-actions", type=int, default=40, help="Max actions per game")

    sc_sub.add_parser("next", help="End current game, start next in scorecard")
    sc_sub.add_parser("status", help="Show scorecard progress and scores")
    sc_sub.add_parser("close", help="Close scorecard and compute final score")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    from arcagi3.cli.commands import (
        cmd_action,
        cmd_end,
        cmd_info,
        cmd_list_games,
        cmd_scorecard_close,
        cmd_scorecard_next,
        cmd_scorecard_open,
        cmd_scorecard_status,
        cmd_start,
        cmd_state,
    )

    try:
        if args.command == "list-games":
            cmd_list_games(args.backend)
        elif args.command == "start":
            cmd_start(args.game_id, args.backend, args.max_actions)
        elif args.command == "action":
            cmd_action(args.action_name, x=args.x, y=args.y, image=args.image)
        elif args.command == "state":
            cmd_state(image=args.image)
        elif args.command == "end":
            cmd_end()
        elif args.command == "info":
            cmd_info()
        elif args.command == "scorecard":
            if args.sc_command == "open":
                cmd_scorecard_open(args.max_actions)
            elif args.sc_command == "next":
                cmd_scorecard_next()
            elif args.sc_command == "status":
                cmd_scorecard_status()
            elif args.sc_command == "close":
                cmd_scorecard_close()
            else:
                p_sc.print_help()
                sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
