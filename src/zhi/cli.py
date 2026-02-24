"""CLI entry point for zhi.

Handles argument parsing and dispatches to REPL, one-shot, or skill run modes.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Any

from zhi.agent import safe_parse_args
from zhi.i18n import prepend_preamble, set_language, t

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="zhi",
        description=t("cli.description"),
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help=t("cli.version_help"),
    )
    parser.add_argument(
        "-c",
        "--command",
        type=str,
        metavar="MESSAGE",
        help=t("cli.command_help"),
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help=t("cli.setup_help"),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help=t("cli.debug_help"),
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help=t("cli.nocolor_help"),
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        metavar="LANG",
        help=t("cli.language_help"),
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    subparsers.add_parser(
        "update",
        help=t("cli.update_help"),
    )

    run_parser = subparsers.add_parser(
        "run",
        help=t("cli.run_help"),
    )
    run_parser.add_argument(
        "skill",
        type=str,
        help=t("cli.skill_help"),
    )
    run_parser.add_argument(
        "files",
        nargs="*",
        help=t("cli.files_help"),
    )

    return parser


def _setup_logging(debug: bool = False, *, config_level: str | None = None) -> None:
    """Configure logging level.

    Args:
        debug: If True, force DEBUG level (overrides config_level).
        config_level: Log level from config (e.g. "INFO", "WARNING").
    """
    if debug:
        level = logging.DEBUG
    elif config_level:
        level = getattr(logging, config_level.upper(), logging.WARNING)
    else:
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
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
    output_dir: str | None = None,
) -> Any:
    """Build an agent Context from config and options."""
    from zhi.agent import Context, PermissionMode
    from zhi.client import Client
    from zhi.skills import _default_user_skills_dir, discover_skills
    from zhi.tools import create_default_registry, register_skill_tools
    from zhi.tools.ocr import OcrTool
    from zhi.tools.shell import ShellTool
    from zhi.tools.skill_create import SkillCreateTool

    def _ask_user_cli(question: str, options: list[str] | None) -> str:
        """Prompt the user for input during agent execution."""
        ui.print(f"\n? {question}")
        if options:
            for i, opt in enumerate(options, 1):
                ui.print(f"  {i}. {opt}")
        answer = input("> ")
        if options and answer.strip().isdigit():
            idx = int(answer.strip()) - 1
            if 0 <= idx < len(options):
                return options[idx]
        return answer.strip()

    effective_output_dir = output_dir or config.output_dir
    client = Client(api_key=config.api_key)
    registry = create_default_registry(
        output_dir=effective_output_dir,
        ask_user_callback=_ask_user_cli,
    )

    # Register tools that need runtime dependencies.
    # ShellTool's own callback auto-approves because the agent loop already
    # gates risky tools through on_permission (no double prompting).
    registry.register(OcrTool(client=client))
    registry.register(ShellTool(permission_callback=lambda _cmd, _destructive: True))

    # Build permission callback (shared with skills via closure)
    def on_permission(tool: Any, call: dict[str, Any]) -> bool:
        return ui.ask_permission(
            tool.name,
            safe_parse_args(call["function"]["arguments"]),
        )

    # We'll create a mutable container so SkillTools can read the live
    # permission_mode even after /auto changes it.
    # The context object is created below; skills get a getter lambda
    # that reads from it.
    context_holder: list[Any] = []

    def permission_mode_getter() -> PermissionMode:
        if context_holder:
            return context_holder[0].permission_mode
        return PermissionMode.APPROVE

    # Register discovered skills as callable tools
    skills = discover_skills()
    register_skill_tools(
        registry,
        skills,
        client,
        on_permission=on_permission,
        permission_mode_getter=permission_mode_getter,
        on_ask_user=_ask_user_cli,
        base_output_dir=config.output_dir,
    )

    # Register skill_create so the LLM can create new user skills
    user_skills_dir = _default_user_skills_dir()
    base_tool_names = [n for n in registry.list_names() if not n.startswith("skill_")]
    registry.register(
        SkillCreateTool(
            user_skills_dir,
            base_tool_names,
            default_model=config.skill_model,
        )
    )

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

    context = Context(
        config=config,
        client=client,
        model=model or config.default_model,
        tools=tools,
        tool_schemas=tool_schemas,
        permission_mode=PermissionMode.APPROVE,
        conversation=conversation,
        max_turns=max_turns or config.max_turns,
        on_stream_start=ui.stream_start,
        on_stream=ui.stream,
        on_thinking=ui.show_thinking,
        on_tool_start=ui.show_tool_start,
        on_tool_end=ui.show_tool_end,
        on_tool_total=ui.set_tool_total,
        on_permission=on_permission,
        on_ask_user=_ask_user_cli,
        on_waiting=ui.show_waiting,
        on_waiting_done=ui.clear_waiting,
    )

    # Wire up the context holder so permission_mode_getter works
    context_holder.append(context)

    return context


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
    t0 = time.monotonic()
    try:
        result = agent_run(context)
    except KeyboardInterrupt:
        print(t("repl.interrupted"))
        return
    except Exception as e:
        logger.exception("Agent error in one-shot mode")
        ui.show_error(ApiError(str(e), suggestions=[t("repl.error_try_again")]))
        sys.exit(1)
    elapsed = time.monotonic() - t0
    if result:
        ui.stream_end()
    if context.files_read or context.files_written:
        ui.show_summary(
            files_read=context.files_read,
            files_written=context.files_written,
            elapsed=elapsed,
        )


def _run_skill(config: Any, ui: Any, skill_name: str, files: list[str]) -> None:
    """Run a skill by name with optional input files."""
    from pathlib import Path

    from zhi.agent import run as agent_run
    from zhi.errors import ApiError
    from zhi.skills import discover_skills

    skills = discover_skills()
    if skill_name not in skills:
        available = ", ".join(sorted(skills.keys())) if skills else "(none)"
        print(t("cli.unknown_skill", skill=skill_name, available=available))
        sys.exit(1)

    skill = skills[skill_name]

    # Read file content upfront and inject into user message (like Claude Code).
    user_content = f"Run the '{skill_name}' skill."
    if files:
        from zhi.client import Client
        from zhi.files import _extract_one

        client = Client(api_key=config.api_key)
        file_sections = []
        for file_path in files:
            path = Path(file_path).expanduser().resolve()
            att = _extract_one(path, client)
            if att.error:
                file_sections.append(
                    f"--- File: {att.filename} ---\n[Error: {att.error}]"
                )
            else:
                file_sections.append(f"--- File: {att.filename} ---\n{att.content}")
        user_content += "\n\n" + "\n\n".join(file_sections)

    skill_output_dir = str(Path(config.output_dir) / skill_name)
    context = _build_context(
        config,
        ui,
        model=skill.model,
        tool_names=skill.tools,
        system_prompt=prepend_preamble(skill.system_prompt),
        user_message=user_content,
        max_turns=skill.max_turns,
        output_dir=skill_output_dir,
    )
    t0 = time.monotonic()
    try:
        result = agent_run(context)
    except KeyboardInterrupt:
        print(t("repl.interrupted"))
        return
    except Exception as e:
        logger.exception("Agent error in skill mode")
        ui.show_error(ApiError(str(e), suggestions=[t("repl.error_try_again")]))
        sys.exit(1)
    elapsed = time.monotonic() - t0
    if result:
        ui.stream_end()
    if context.files_read or context.files_written:
        ui.show_summary(
            files_read=context.files_read,
            files_written=context.files_written,
            elapsed=elapsed,
        )


def _run_pipe(config: Any, ui: Any) -> None:
    """Read stdin and run through the agent."""
    stdin_text = sys.stdin.read().strip()
    if not stdin_text:
        print(t("cli.no_stdin"))
        sys.exit(1)
    _run_oneshot(config, ui, stdin_text)


def _run_update() -> None:
    """Run the update subcommand."""
    from zhi.updater import perform_update

    success, message = perform_update()
    print(message)
    if not success:
        sys.exit(1)


def _maybe_check_update(config: Any) -> None:
    """Show a notice if a new version is available (non-blocking, cached).

    Skipped when:
    - ZHI_NO_UPDATE_CHECK=1 is set
    - config.auto_update_check is False
    """
    if os.environ.get("ZHI_NO_UPDATE_CHECK") == "1":
        return
    if not getattr(config, "auto_update_check", True):
        return

    from zhi import __version__
    from zhi.updater import check_for_update, cleanup_old_exe

    # Clean up leftover .old exe from previous update
    cleanup_old_exe()

    result = check_for_update(__version__)
    if result is not None:
        print(t("update.available", current=result["current"], latest=result["latest"]))


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

    # Handle --debug (initial, may be overridden after config load)
    _setup_logging(debug=args.debug)

    # Handle --language
    if args.language:
        set_language(args.language)

    # Handle --setup
    if args.setup:
        from zhi.config import run_wizard

        run_wizard()
        return

    # Handle 'update' subcommand (no API key needed)
    if args.subcommand == "update":
        _run_update()
        return

    # Load config for all remaining modes
    from zhi.config import load_config
    from zhi.ui import UI

    config = load_config()

    # Re-apply logging with config level (--debug still overrides)
    _setup_logging(debug=args.debug, config_level=config.log_level)

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

    # Check for updates on REPL startup (cached, non-blocking)
    _maybe_check_update(config)

    _run_repl(config, ui)
