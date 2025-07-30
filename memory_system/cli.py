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

    # Monitoring dashboard (placeholder)
    subparsers.add_parser("monitor", help="Launch real-time monitoring dashboard (TUI)")

    # Architecture Mode commands
    arch_parser = subparsers.add_parser("arch-mode", help="Architecture-first planning and development workflow")
    arch_subparsers = arch_parser.add_subparsers(dest="arch_command")
    
    # Activate Architecture Mode
    arch_subparsers.add_parser("activate", help="Activate architecture-first planning mode")
    
    # Load Project Brain
    load_parser = arch_subparsers.add_parser("load-brain", help="Load project brain context into memory")
    load_parser.add_argument("--domains", type=str, help="Comma-separated list of brain domains to load (e.g., core,modules)")
    load_parser.add_argument("--priority", type=int, choices=[1, 2, 3], help="Load only sections with specified priority or higher")
    
    # Create Architecture Plan
    plan_parser = arch_subparsers.add_parser("plan", help="Generate comprehensive architecture plan")
    plan_parser.add_argument("description", help="Feature or requirement description to plan")
    plan_parser.add_argument("--template", type=str, help="Template to use for plan generation")
    plan_parser.add_argument("--output", type=str, help="Output file for the generated plan")
    
    # Validate Plan
    validate_parser = arch_subparsers.add_parser("validate", help="Validate architecture plan against project constraints")
    validate_parser.add_argument("plan_id", help="Plan ID or file path to validate")
    validate_parser.add_argument("--strict", action="store_true", help="Enable strict validation mode")
    
    # Approve Plan
    approve_parser = arch_subparsers.add_parser("approve", help="Approve plan and prepare for implementation")
    approve_parser.add_argument("plan_id", help="Plan ID or file path to approve")
    approve_parser.add_argument("--auto-generate-tasks", action="store_true", help="Automatically generate implementation tasks")
    
    # List Plans
    list_parser = arch_subparsers.add_parser("list", help="List all architecture plans")
    list_parser.add_argument("--status", choices=["draft", "validated", "approved", "implemented"], help="Filter by plan status")
    
    # Plan Status
    status_parser = arch_subparsers.add_parser("status", help="Show status of specific plan or overview")
    status_parser.add_argument("plan_id", nargs="?", help="Plan ID to show status for (optional)")
    
    # Generate Implementation Prompts
    prompts_parser = arch_subparsers.add_parser("generate-prompts", help="Generate ready-to-use implementation prompts")
    prompts_parser.add_argument("plan_id", help="Plan ID to generate prompts for")
    prompts_parser.add_argument("--output-dir", type=str, help="Directory to save prompt files (default: architecture-plans/prompts/)")
    prompts_parser.add_argument("--format", choices=["markdown", "text", "json"], default="markdown", help="Output format for prompts")

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
    elif args.command == "monitor":
        from memory_system.monitor import run_dashboard

        run_dashboard()
    elif args.command == "arch-mode":
        from architecture_mode_engine import handle_arch_mode_command
        
        handle_arch_mode_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main(sys.argv[1:])