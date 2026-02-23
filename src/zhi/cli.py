"""CLI entry point for zhi.

Handles argument parsing and dispatches to REPL, one-shot, or skill run modes.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="zhi",
        description="Agentic CLI powered by Zhipu GLM models",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )
    parser.add_argument(
        "-c",
        "--command",
        type=str,
        metavar="MESSAGE",
        help="One-shot mode: send a single message and exit",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Re-run the setup wizard",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    run_parser = subparsers.add_parser(
        "run",
        help="Run a skill",
    )
    run_parser.add_argument(
        "skill",
        type=str,
        help="Name of the skill to run",
    )
    run_parser.add_argument(
        "files",
        nargs="*",
        help="Input files for the skill",
    )

    return parser


def _setup_logging(debug: bool = False) -> None:
    """Configure logging level."""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the zhi CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Handle --version
    if args.version:
        from zhi import __version__

        print(f"zhi {__version__}")
        return

    # Handle --no-color
    if args.no_color or os.environ.get("NO_COLOR"):
        os.environ["NO_COLOR"] = "1"

    # Handle --debug
    _setup_logging(debug=args.debug)

    # Handle --setup
    if args.setup:
        from zhi.config import run_wizard

        run_wizard()
        return

    # Handle 'run' subcommand
    if args.subcommand == "run":
        print(f"Skill run not yet implemented: {args.skill}")
        return

    # Handle one-shot mode (-c)
    if args.command:
        print(f"One-shot mode not yet implemented: {args.command}")
        return

    # Detect pipe mode
    is_interactive = sys.stdin.isatty()

    if not is_interactive:
        # Pipe mode: read stdin and process
        print("Pipe mode not yet implemented.")
        return

    # Default: launch REPL
    from zhi.config import load_config

    config = load_config()
    if not config.has_api_key:
        from zhi.config import run_wizard

        run_wizard()
        return

    print("REPL not yet implemented. Run `zhi --setup` to configure.")
