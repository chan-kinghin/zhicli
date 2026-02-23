"""CLI entry point for zhi.

Handles argument parsing and dispatches to REPL, one-shot, or skill run modes.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

from zhi.agent import safe_parse_args
from zhi.i18n import prepend_preamble, set_language, t

logger = logging.getLogger(__name__)


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
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        metavar="LANG",
        help=t("cli.language_help"),
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


def _build_context(
    config: Any,
    ui: Any,
    *,
    model: str | None = None,
    tool_names: list[str] | None = None,
    system_prompt: str | None = None,
    user_message: str | None = None,
    max_turns: int | None = None,
) -> Any:
    """Build an agent Context from config and options."""
    from zhi.agent import Context, PermissionMode
    from zhi.client import Client
    from zhi.skills import discover_skills
    from zhi.tools import create_default_registry, register_skill_tools
    from zhi.tools.ocr import OcrTool
    from zhi.tools.shell import ShellTool

    client = Client(api_key=config.api_key)
    registry = create_default_registry()

    # Register tools that need runtime dependencies.
    # ShellTool's own callback auto-approves because the agent loop already
    # gates risky tools through on_permission (no double prompting).
    registry.register(OcrTool(client=client))
    registry.register(ShellTool(permission_callback=lambda _cmd, _destructive: True))

    # Register discovered skills as callable tools
    skills = discover_skills()
    register_skill_tools(registry, skills, client)

    if tool_names is not None:
        tools = registry.filter_by_names(tool_names)
        tool_schemas = registry.to_schemas_filtered(tool_names)
    else:
        tools = {t.name: t for t in registry.list_tools()}
        tool_schemas = registry.to_schemas()

    conversation: list[dict[str, Any]] = []
    if system_prompt:
        conversation.append({"role": "system", "content": system_prompt})
    if user_message:
        conversation.append({"role": "user", "content": user_message})

    return Context(
        config=config,
        client=client,
        model=model or config.default_model,
        tools=tools,
        tool_schemas=tool_schemas,
        permission_mode=PermissionMode.APPROVE,
        conversation=conversation,
        max_turns=max_turns or config.max_turns,
        on_stream=ui.stream,
        on_thinking=ui.show_thinking,
        on_tool_start=ui.show_tool_start,
        on_tool_end=ui.show_tool_end,
        on_permission=lambda tool, call: ui.ask_permission(
            tool.name,
            safe_parse_args(call["function"]["arguments"]),
        ),
        on_waiting=ui.show_waiting,
        on_waiting_done=ui.clear_waiting,
    )


def _require_api_key(config: Any) -> bool:
    """Check API key and print error if missing. Returns True if key exists."""
    if not config.has_api_key:
        print(t("cli.no_api_key"))
        return False
    return True


def _run_oneshot(config: Any, ui: Any, message: str) -> None:
    """Run a single message through the agent and exit."""
    from zhi.agent import run as agent_run
    from zhi.errors import ApiError

    context = _build_context(config, ui, user_message=message)
    try:
        result = agent_run(context)
    except KeyboardInterrupt:
        print(t("repl.interrupted"))
        return
    except Exception as e:
        logger.exception("Agent error in one-shot mode")
        ui.show_error(ApiError(str(e), suggestions=[t("repl.error_try_again")]))
        sys.exit(1)
    if result:
        ui.stream_end()


def _run_skill(config: Any, ui: Any, skill_name: str, files: list[str]) -> None:
    """Run a skill by name with optional input files."""
    from zhi.agent import run as agent_run
    from zhi.errors import ApiError
    from zhi.skills import discover_skills

    skills = discover_skills()
    if skill_name not in skills:
        available = ", ".join(sorted(skills.keys())) if skills else "(none)"
        print(t("cli.unknown_skill", skill=skill_name, available=available))
        sys.exit(1)

    skill = skills[skill_name]

    user_content = f"Run the '{skill_name}' skill."
    if files:
        file_list = ", ".join(files)
        user_content += f" Input files: {file_list}"

    context = _build_context(
        config,
        ui,
        model=skill.model,
        tool_names=skill.tools,
        system_prompt=prepend_preamble(skill.system_prompt),
        user_message=user_content,
        max_turns=skill.max_turns,
    )
    try:
        result = agent_run(context)
    except KeyboardInterrupt:
        print(t("repl.interrupted"))
        return
    except Exception as e:
        logger.exception("Agent error in skill mode")
        ui.show_error(ApiError(str(e), suggestions=[t("repl.error_try_again")]))
        sys.exit(1)
    if result:
        ui.stream_end()


def _run_pipe(config: Any, ui: Any) -> None:
    """Read stdin and run through the agent."""
    stdin_text = sys.stdin.read().strip()
    if not stdin_text:
        print(t("cli.no_stdin"))
        sys.exit(1)
    _run_oneshot(config, ui, stdin_text)


def _run_repl(config: Any, ui: Any) -> None:
    """Launch the interactive REPL."""
    from zhi.repl import ReplSession

    context = _build_context(config, ui)
    session = ReplSession(context=context, ui=ui)
    session.run()


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

    # Handle --language
    if args.language:
        set_language(args.language)

    # Handle --setup
    if args.setup:
        from zhi.config import run_wizard

        run_wizard()
        return

    # Load config for all remaining modes
    from zhi.config import load_config
    from zhi.ui import UI

    config = load_config()

    # Apply language from config
    if not args.language and config.language != "auto":
        set_language(config.language)

    ui = UI(no_color=bool(os.environ.get("NO_COLOR")))

    # Handle 'run' subcommand
    if args.subcommand == "run":
        if not _require_api_key(config):
            sys.exit(1)
        _run_skill(config, ui, args.skill, args.files)
        return

    # Handle one-shot mode (-c)
    if args.command:
        if not _require_api_key(config):
            sys.exit(1)
        _run_oneshot(config, ui, args.command)
        return

    # Detect pipe mode
    if not sys.stdin.isatty():
        if not _require_api_key(config):
            sys.exit(1)
        _run_pipe(config, ui)
        return

    # Default: launch REPL
    if not config.has_api_key:
        from zhi.config import run_wizard

        run_wizard()
        return

    _run_repl(config, ui)
