"""Unified Memory System CLI (skeleton).

This CLI will eventually replace assorted shell helpers.  For now it can launch the
Task Command Center and serve as a placeholder for future subcommands.
"""
import argparse
import sys


def main(argv: list[str] | None = None) -> None:  # noqa: D401
    """Entry point for the `memoryctl` command."""
    parser = argparse.ArgumentParser(
        prog="memoryctl",
        description="Unified Memory System CLI (skeleton)",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Existing Task Command Center launcher
    subparsers.add_parser("tcc", help="Launch Task Command Center UI")

    args = parser.parse_args(argv)

    if args.command == "tcc":
        from task_command_center import main as tcc_main

        tcc_main()
    else:
        parser.print_help()


if __name__ == "__main__":
    main(sys.argv[1:])