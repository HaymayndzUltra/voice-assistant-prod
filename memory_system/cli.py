"""Unified Memory System CLI (skeleton).

This CLI will eventually replace assorted shell helpers.  For now it can launch the
Task Command Center and serve as a placeholder for future subcommands.
"""
import argparse
import sys
from typing import List, Optional

from memory_system import logger as _ms_logger


def main(argv: Optional[List[str]] = None) -> None:  # noqa: D401
    """Entry point for the `memoryctl` command."""
    # Ensure JSON logging configured
    _ms_logger.setup()

    parser = argparse.ArgumentParser(
        prog="memoryctl",
        description="Unified Memory System CLI (skeleton)",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Existing Task Command Center launcher
    subparsers.add_parser("tcc", help="Launch Task Command Center UI")

    # Async Task Engine runner
    run_parser = subparsers.add_parser("run", help="Execute one or more tasks concurrently")
    run_parser.add_argument("tasks", nargs="+", help="One or more task descriptions to execute intelligently")
    run_parser.add_argument("--workers", "-w", type=int, default=5, help="Maximum concurrent workers (default: 5)")

    # Memory migration helper
    migrate_parser = subparsers.add_parser("migrate", help="Migrate markdown memories into SQLite DB")
    migrate_parser.add_argument("--to", choices=["sqlite"], required=True, help="Target provider kind")

    args = parser.parse_args(argv)

    if args.command == "tcc":
        from task_command_center import main as tcc_main

        tcc_main()
    elif args.command == "run":
        from memory_system.services.async_task_engine import run_tasks_concurrently

        results = run_tasks_concurrently(args.tasks, max_workers=args.workers)
        import json as _json

        print("\n📊 Execution Summary:\n" + _json.dumps(results, indent=2))
    elif args.command == "migrate":
        from memory_system.scripts.migrate_memories import main as migrate_main

        migrate_main(["--to", args.to])
    else:
        parser.print_help()


if __name__ == "__main__":
    main(sys.argv[1:])