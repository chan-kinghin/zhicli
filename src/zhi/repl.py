"""Interactive REPL loop with slash commands, history, and tab completion.

Uses prompt_toolkit for input with persistent history, tab completion,
multi-line input, and CJK/IME support.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any

import platformdirs
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory, InMemoryHistory

from zhi.agent import (
    AgentInterruptedError,
    Context,
    PermissionMode,
    Role,
    safe_parse_args,
)
from zhi.agent import run as agent_run
from zhi.files import FileAttachment, extract_files
from zhi.i18n import prepend_preamble, t
from zhi.models import MODELS, is_valid_model
from zhi.ui import UI

logger = logging.getLogger(__name__)

# Lines matching these patterns are excluded from history
_SENSITIVE_PATTERNS = re.compile(r"(api_key|password|token|secret)", re.IGNORECASE)

# Canonical set of slash commands — used by both dispatch and completer.
# Add new commands here AND in _handle_command's handlers dict.
_SLASH_COMMANDS = frozenset(
    {
        "/help",
        "/auto",
        "/approve",
        "/model",
        "/think",
        "/fast",
        "/exit",
        "/run",
        "/skill",
        "/status",
        "/reset",
        "/undo",
        "/usage",
        "/verbose",
    }
)

_MAX_HISTORY_ENTRIES = 10_000
_SKILLS_CACHE_TTL = 5.0  # seconds


class _SkillsCache:
    """Simple TTL cache for discover_skills() to avoid re-scanning on every call."""

    def __init__(self, ttl: float = _SKILLS_CACHE_TTL) -> None:
        self._ttl = ttl
        self._cache: dict[str, Any] | None = None
        self._last_fetch: float = 0.0

    def get(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._cache is None or (now - self._last_fetch) > self._ttl:
            from zhi.skills import discover_skills

            self._cache = discover_skills()
            self._last_fetch = now
        return self._cache

    def invalidate(self) -> None:
        self._cache = None


class _FilteredFileHistory(FileHistory):
    """File history that excludes lines containing sensitive patterns."""

    def store_string(self, string: str) -> None:
        if _SENSITIVE_PATTERNS.search(string):
            return
        super().store_string(string)


class _ZhiCompleter(Completer):
    """Context-aware completer for zhi REPL."""

    def __init__(
        self,
        commands: list[str],
        models: list[str],
        skills_fn: Any,
    ) -> None:
        self._commands = commands
        self._models = models
        self._skills_fn = skills_fn

    def get_completions(self, document: Any, complete_event: Any) -> Any:
        text = document.text_before_cursor
        if text.startswith("/run "):
            prefix = text[len("/run ") :]
            for name in sorted(self._skills_fn()):
                if name.startswith(prefix):
                    yield Completion(name, start_position=-len(prefix))
        elif text.startswith("/model "):
            prefix = text[len("/model ") :]
            for name in self._models:
                if name.startswith(prefix):
                    yield Completion(name, start_position=-len(prefix))
        elif text.startswith("/skill "):
            prefix = text[len("/skill ") :]
            for sub in ["list", "new", "show", "edit", "delete"]:
                if sub.startswith(prefix):
                    yield Completion(sub, start_position=-len(prefix))
        elif text.startswith("/"):
            for cmd in self._commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))


class ReplSession:
    """Interactive REPL session with slash commands and agent integration."""

    def __init__(
        self,
        context: Context,
        ui: UI,
        *,
        history_path: Path | None = None,
    ) -> None:
        self._context = context
        self._ui = ui
        self._running = False

        # Set up history
        if history_path is None:
            config_dir = Path(platformdirs.user_config_dir("zhi"))
            config_dir.mkdir(parents=True, exist_ok=True)
            history_path = config_dir / "history.txt"

        try:
            self._history: FileHistory | InMemoryHistory = _FilteredFileHistory(
                str(history_path)
            )
        except OSError:
            logger.warning("Could not open history file, using in-memory history")
            self._history = InMemoryHistory()

        # Set up skills cache and tab completion
        self._skills_cache = _SkillsCache()

        self._completer = _ZhiCompleter(
            commands=list(_SLASH_COMMANDS),
            models=list(MODELS.keys()),
            skills_fn=lambda: list(self._skills_cache.get().keys()),
        )

        from zhi.keybindings import create_key_bindings

        toolbar = self._get_toolbar if not ui._no_color else None
        self._session: PromptSession[str] = PromptSession(
            history=self._history,
            completer=self._completer,
            key_bindings=create_key_bindings(),
            multiline=True,
            bottom_toolbar=toolbar,
        )

    def _get_prompt(self) -> str:
        """Get the prompt string."""
        return "zhi> "

    @staticmethod
    def _prompt_continuation(width: int, line_number: int, is_soft_wrap: bool) -> str:
        """Return continuation prompt for multi-line input."""
        return "...  "

    def _get_toolbar(self) -> HTML:
        """Return bottom toolbar content showing session state."""
        thinking = t("repl.on") if self._context.thinking_enabled else t("repl.off")
        tokens = f"{self._context.session_tokens:,}"
        parts = [
            f" {self._context.model}",
            f"{t('toolbar.mode')}: {self._context.permission_mode.value}",
            f"{t('toolbar.think')}: {thinking}",
            f"{t('toolbar.tokens')}: {tokens}",
        ]
        return HTML(f"<b>{' | '.join(parts)}</b>")

    def run(self) -> None:
        """Run the REPL loop until /exit or Ctrl+D."""
        self._running = True
        from zhi import __version__

        self._ui.show_banner(__version__)

        while self._running:
            try:
                user_input = self._session.prompt(
                    self._get_prompt(),
                    prompt_continuation=self._prompt_continuation,
                )
            except KeyboardInterrupt:
                # Ctrl+C: cancel current input, return to prompt
                continue
            except EOFError:
                # Ctrl+D: exit gracefully
                self._handle_exit()
                break

            if not user_input.strip():
                continue

            self.handle_input(user_input.strip())

    def handle_input(self, text: str) -> str | None:
        """Handle user input: detect files, dispatch commands, or send to agent."""
        # Dispatch slash commands FIRST — before extract_files, so that
        # /run receives the original text with real file paths intact.
        if text.startswith("/"):
            first_word = text.split(maxsplit=1)[0].lower()
            if first_word in _SLASH_COMMANDS:
                return self._handle_command(text)

        # Extract files only for chat input (not slash commands)
        cleaned_text, attachments = extract_files(text, self._context.client)

        # Show feedback if files were attached
        if attachments:
            successful = [a for a in attachments if a.error is None]
            errors = [a for a in attachments if a.error is not None]
            if successful:
                self._ui.print(t("files.extracted", count=len(successful)))
            for att in errors:
                self._ui.print(
                    t("files.extract_error", path=att.filename, error=att.error)
                )

        return self._handle_chat(cleaned_text, attachments=attachments)

    def _handle_command(self, text: str) -> str | None:
        """Dispatch slash commands."""
        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handlers: dict[str, Any] = {
            "/help": self._handle_help,
            "/auto": self._handle_auto,
            "/approve": self._handle_approve,
            "/model": self._handle_model,
            "/think": self._handle_think,
            "/fast": self._handle_fast,
            "/exit": self._handle_exit,
            "/run": self._handle_run,
            "/skill": self._handle_skill,
            "/status": self._handle_status,
            "/reset": self._handle_reset,
            "/undo": self._handle_undo,
            "/usage": self._handle_usage,
            "/verbose": self._handle_verbose,
        }
        assert set(handlers) == _SLASH_COMMANDS, (
            f"_SLASH_COMMANDS and handlers dict out of sync: "
            f"missing handlers={_SLASH_COMMANDS - set(handlers)}, "
            f"extra handlers={set(handlers) - _SLASH_COMMANDS}"
        )

        handler = handlers.get(command)
        if handler is None:
            msg = t("repl.unknown_cmd", command=command)
            self._ui.print(msg)
            return msg

        return handler(args)

    def _handle_help(self, _args: str = "") -> str:
        """Show available commands."""
        help_text = t("repl.help")
        self._ui.print(help_text)
        return help_text

    def _handle_auto(self, _args: str = "") -> str:
        """Switch to auto mode."""
        self._context.permission_mode = PermissionMode.AUTO
        msg = t("repl.mode_auto")
        self._ui.print(msg)
        return msg

    def _handle_approve(self, _args: str = "") -> str:
        """Switch to approve mode."""
        self._context.permission_mode = PermissionMode.APPROVE
        msg = t("repl.mode_approve")
        self._ui.print(msg)
        return msg

    def _handle_model(self, args: str = "") -> str:
        """Switch the model for the current session."""
        model_name = args.strip()
        if not model_name:
            available = ", ".join(MODELS.keys())
            msg = t(
                "repl.current_model", model=self._context.model, available=available
            )
            self._ui.print(msg)
            return msg

        if not is_valid_model(model_name):
            msg = t(
                "repl.unknown_model",
                model=model_name,
                available=", ".join(MODELS.keys()),
            )
            self._ui.print(msg)
            return msg

        self._context.model = model_name
        msg = t("repl.model_switched", model=model_name)
        self._ui.print(msg)
        return msg

    def _handle_think(self, _args: str = "") -> str:
        """Enable thinking mode."""
        self._context.thinking_enabled = True
        msg = t("repl.think_on")
        self._ui.print(msg)
        return msg

    def _handle_fast(self, _args: str = "") -> str:
        """Disable thinking mode."""
        self._context.thinking_enabled = False
        msg = t("repl.think_off")
        self._ui.print(msg)
        return msg

    def _handle_status(self, _args: str = "") -> str:
        """Show current session state."""
        thinking = t("repl.on") if self._context.thinking_enabled else t("repl.off")
        verbose = t("repl.on") if self._ui.verbose else t("repl.off")
        turns = len([m for m in self._context.conversation if m.get("role") == "user"])
        msg = t(
            "repl.status",
            model=self._context.model,
            mode=self._context.permission_mode.value,
            thinking=thinking,
            verbose=verbose,
            turns=str(turns),
            tokens=str(self._context.session_tokens),
        )
        self._ui.print(msg)
        return msg

    def _handle_exit(self, _args: str = "") -> str:
        """Exit the REPL."""
        self._running = False
        if self._context.session_tokens > 0:
            self._ui.show_usage(self._context.session_tokens)
        msg = t("repl.goodbye")
        self._ui.print(msg)
        return msg

    def _handle_run(self, args: str = "") -> str:
        """Run a skill by name with optional file arguments."""
        if not args.strip():
            msg = t("repl.run_usage")
            self._ui.print(msg)
            return msg

        # Use shlex to properly handle quoted paths and escaped spaces:
        #   /run compare "file one.xlsx" file2.xlsx
        #   /run compare file\ one.xlsx file2.xlsx
        import shlex

        try:
            parts = shlex.split(args.strip())
        except ValueError as exc:
            msg = t("repl.run_parse_error", error=str(exc))
            self._ui.print(msg)
            return msg

        if not parts:
            msg = t("repl.run_usage")
            self._ui.print(msg)
            return msg

        skill_name = parts[0]
        files = parts[1:]

        skills = self._skills_cache.get()
        if skill_name not in skills:
            available = ", ".join(sorted(skills.keys())) if skills else "(none)"
            msg = t("repl.unknown_skill", skill=skill_name, available=available)
            self._ui.print(msg)
            return msg

        skill = skills[skill_name]

        # Read file content upfront and inject into user message (like Claude Code).
        user_content = f"Run the '{skill_name}' skill."
        if files:
            from zhi.files import _extract_one

            file_sections: list[str] = []
            for file_path in files:
                path = Path(file_path).expanduser().resolve()
                att = _extract_one(path, self._context.client)
                if att.error:
                    file_sections.append(
                        f"--- File: {att.filename} ---\n[Error: {att.error}]"
                    )
                else:
                    file_sections.append(f"--- File: {att.filename} ---\n{att.content}")
            user_content += "\n\n" + "\n\n".join(file_sections)

        # Build a skill-scoped context from the current context's client
        from zhi.tools import ToolRegistry, register_skill_tools

        skill_registry = ToolRegistry()
        # Register base tools the skill needs (warn on missing — Bug 8)
        for tool_name in skill.tools:
            existing = self._context.tools.get(tool_name)
            if existing is not None:
                skill_registry.register(existing)
            else:
                self._ui.show_warning(
                    f"Skill '{skill_name}' references unknown tool '{tool_name}'"
                )

        # Also register skill-tools for composition
        register_skill_tools(skill_registry, skills, self._context.client)

        skill_tools = skill_registry.filter_by_names(skill.tools)
        # Also include skill_ prefixed versions
        for t_name in skill.tools:
            prefixed = f"skill_{t_name}"
            st = skill_registry.get(prefixed)
            if st is not None:
                skill_tools[prefixed] = st

        skill_schemas = [
            tool_obj.to_function_schema() for tool_obj in skill_tools.values()
        ]

        conversation: list[dict[str, Any]] = []
        if skill.system_prompt:
            conversation.append(
                {
                    "role": Role.SYSTEM.value,
                    "content": prepend_preamble(skill.system_prompt),
                }
            )
        conversation.append({"role": Role.USER.value, "content": user_content})

        def _ask_user_repl(question: str, options: list[str] | None) -> str:
            """Prompt the user for input during skill execution."""
            from prompt_toolkit import prompt as pt_prompt

            self._ui.stream_end()
            self._ui.print(f"\n? {question}")
            if options:
                for i, opt in enumerate(options, 1):
                    self._ui.print(f"  {i}. {opt}")
            answer = pt_prompt("> ")
            if options and answer.strip().isdigit():
                idx = int(answer.strip()) - 1
                if 0 <= idx < len(options):
                    return options[idx]
            return answer.strip()

        skill_context = Context(
            config=self._context.config,
            client=self._context.client,
            model=skill.model,
            tools=skill_tools,
            tool_schemas=skill_schemas,
            permission_mode=self._context.permission_mode,
            conversation=conversation,
            max_turns=skill.max_turns,
            on_stream_start=self._ui.stream_start,
            on_stream=self._ui.stream,
            on_thinking=self._ui.show_thinking,
            on_tool_start=self._ui.show_tool_start,
            on_tool_end=self._ui.show_tool_end,
            on_tool_total=self._ui.set_tool_total,
            on_permission=lambda tool, call: self._ui.ask_permission(
                tool.name,
                safe_parse_args(call["function"]["arguments"]),
            ),
            on_ask_user=_ask_user_repl,
            on_waiting=self._ui.show_waiting,
            on_waiting_done=self._ui.clear_waiting,
        )

        # Wire cancel_event from the main context so ESC works (Bug 9)
        skill_context.cancel_event = self._context.cancel_event

        # Set up ESC watcher for skill runs (same as _handle_chat)
        self._context.cancel_event.clear()
        stop_event: threading.Event | None = None
        if sys.stdin.isatty():
            stop_event = self._start_esc_watcher(self._context.cancel_event)

        t0 = time.monotonic()
        try:
            result = agent_run(skill_context)
        except (KeyboardInterrupt, AgentInterruptedError):
            self._ui.print(t("repl.interrupted"))
            return "Interrupted"
        except Exception as e:
            logger.exception("Skill run error")
            msg = t("repl.skill_error", skill=skill_name, error=str(e))
            self._ui.print(msg)
            return msg
        finally:
            # Stop the ESC watcher thread
            if stop_event is not None:
                stop_event.set()
            self._context.cancel_event.clear()
            # Merge skill token usage back into the main session
            self._context.session_tokens += skill_context.session_tokens
        elapsed = time.monotonic() - t0

        if result is None:
            msg = t("repl.skill_max_turns", skill=skill_name)
            self._ui.show_warning(msg)
            return msg

        self._ui.stream_end()

        # Show file summary after skill runs (Bug 17)
        if skill_context.files_read or skill_context.files_written:
            self._ui.show_summary(
                files_read=skill_context.files_read,
                files_written=skill_context.files_written,
                elapsed=elapsed,
            )

        return result

    def _handle_skill(self, args: str = "") -> str:
        """Handle /skill subcommands."""
        parts = args.strip().split(maxsplit=1)
        subcommand = parts[0] if parts else ""

        if subcommand == "list":
            skills = self._skills_cache.get()
            if not skills:
                msg = t("repl.no_skills")
                self._ui.print(msg)
                return msg
            lines = [t("repl.skill_list_title")]
            for name, cfg in sorted(skills.items()):
                source_tag = f" ({cfg.source})" if cfg.source else ""
                lines.append(f"  {name}{source_tag} — {cfg.description}")
            msg = "\n".join(lines)
            self._ui.print(msg)
            return msg
        elif subcommand == "new":
            msg = t("repl.skill_new_todo")
            self._ui.print(msg)
            return msg
        elif subcommand == "show":
            name = parts[1] if len(parts) > 1 else ""
            if not name:
                msg = t("repl.skill_show_usage")
                self._ui.print(msg)
                return msg
            skills = self._skills_cache.get()
            if name not in skills:
                msg = t("repl.skill_not_found", name=name)
                self._ui.print(msg)
                return msg
            skill = skills[name]
            lines = [
                f"Name: {skill.name}",
                f"Description: {skill.description}",
                f"Model: {skill.model}",
                f"Tools: {', '.join(skill.tools)}",
                f"Max turns: {skill.max_turns}",
                f"Source: {skill.source}",
            ]
            msg = "\n".join(lines)
            self._ui.print(msg)
            return msg
        elif subcommand == "edit":
            name = parts[1] if len(parts) > 1 else ""
            if not name:
                msg = t("repl.skill_edit_usage")
                self._ui.print(msg)
                return msg
            skills = self._skills_cache.get()
            if name not in skills:
                msg = t("repl.skill_not_found", name=name)
                self._ui.print(msg)
                return msg
            msg = t("repl.skill_edit_todo")
            self._ui.print(msg)
            return msg
        elif subcommand == "delete":
            name = parts[1] if len(parts) > 1 else ""
            if not name:
                msg = t("repl.skill_delete_usage")
                self._ui.print(msg)
                return msg
            skills = self._skills_cache.get()
            if name not in skills:
                msg = t("repl.skill_not_found", name=name)
                self._ui.print(msg)
                return msg
            msg = t("repl.skill_delete_todo")
            self._ui.print(msg)
            return msg
        else:
            msg = t("repl.skill_usage")
            self._ui.print(msg)
            return msg

    def _handle_reset(self, _args: str = "") -> str:
        """Clear conversation history."""
        try:
            response = self._session.prompt(t("repl.reset_confirm"))
            if response.strip().lower() not in ("y", "yes"):
                return ""
        except (KeyboardInterrupt, EOFError):
            return ""
        # Keep system messages
        self._context.conversation = [
            msg
            for msg in self._context.conversation
            if msg.get("role") == Role.SYSTEM.value
        ]
        msg = t("repl.cleared")
        self._ui.print(msg)
        return msg

    def _handle_undo(self, _args: str = "") -> str:
        """Remove last user message and AI response."""
        # Find the last user message and remove everything after it
        conv = self._context.conversation
        last_user_idx = None
        for i in range(len(conv) - 1, -1, -1):
            if conv[i].get("role") == Role.USER.value:
                last_user_idx = i
                break

        if last_user_idx is None:
            msg = t("repl.nothing_undo")
            self._ui.print(msg)
            return msg

        self._context.conversation = conv[:last_user_idx]
        msg = t("repl.undone")
        self._ui.print(msg)
        return msg

    def _handle_usage(self, _args: str = "") -> str:
        """Show token/cost stats."""
        tokens = self._context.session_tokens
        self._ui.show_usage(tokens)
        msg = f"Tokens: {tokens}"
        return msg

    def _handle_verbose(self, _args: str = "") -> str:
        """Toggle verbose output."""
        self._ui.verbose = not self._ui.verbose
        msg = t("repl.verbose_on") if self._ui.verbose else t("repl.verbose_off")
        self._ui.print(msg)
        return msg

    @staticmethod
    def _start_esc_watcher(cancel_event: threading.Event) -> threading.Event:
        """Start a daemon thread that watches for ESC key to cancel generation.

        Returns a stop_event to signal the watcher to exit.
        """
        stop_event = threading.Event()

        def _watch() -> None:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    while not stop_event.is_set():
                        if msvcrt.kbhit():
                            ch = msvcrt.getch()
                            if ch == b"\x1b":
                                cancel_event.set()
                                return
                        stop_event.wait(0.05)
                else:
                    import select
                    import termios
                    import tty

                    fd = sys.stdin.fileno()
                    try:
                        old_settings = termios.tcgetattr(fd)
                    except termios.error:
                        return  # Not a TTY
                    try:
                        tty.setcbreak(fd)
                        while not stop_event.is_set():
                            ready, _, _ = select.select([fd], [], [], 0.05)
                            if ready:
                                ch = os.read(fd, 1)
                                if ch == b"\x1b":
                                    cancel_event.set()
                                    return
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass  # Silently ignore errors in watcher

        thread = threading.Thread(target=_watch, daemon=True)
        thread.start()
        return stop_event

    def _handle_chat(
        self,
        text: str,
        attachments: list[FileAttachment] | None = None,
    ) -> str | None:
        """Send user text to the agent and display results."""
        # Build content with file attachments
        content = text
        if attachments:
            file_sections = []
            for i, att in enumerate(attachments, 1):
                if att.error:
                    file_sections.append(
                        f"--- File {i}: {att.filename} ---\n[Error: {att.error}]"
                    )
                else:
                    file_sections.append(
                        f"--- File {i}: {att.filename} ---\n{att.content}"
                    )
            content = text + "\n\n" + "\n\n".join(file_sections)

        user_msg = {
            "role": Role.USER.value,
            "content": content,
        }
        self._context.conversation.append(user_msg)

        # Reset file counters for this interaction
        self._context.files_read = 0
        self._context.files_written = 0

        # Set up ESC watcher for cancellation
        self._context.cancel_event.clear()
        stop_event: threading.Event | None = None
        if sys.stdin.isatty():
            stop_event = self._start_esc_watcher(self._context.cancel_event)

        t0 = time.monotonic()
        try:
            result = agent_run(self._context)
        except (KeyboardInterrupt, AgentInterruptedError):
            self._ui.print(t("repl.interrupted"))
            return None
        except Exception as e:
            logger.exception("Agent error")
            conv = self._context.conversation
            if conv and conv[-1] is user_msg:
                self._context.conversation.pop()
            from zhi.errors import ApiError

            self._ui.show_error(
                ApiError(
                    str(e),
                    suggestions=[
                        t("repl.error_try_again"),
                        t("repl.error_check_connection"),
                    ],
                )
            )
            return None
        finally:
            # Stop the ESC watcher thread
            if stop_event is not None:
                stop_event.set()
            self._context.cancel_event.clear()
        elapsed = time.monotonic() - t0

        if result is None:
            self._ui.show_warning(t("repl.max_turns"))
        else:
            self._ui.stream_end()

        # Show summary if files were touched
        if self._context.files_read or self._context.files_written:
            self._ui.show_summary(
                files_read=self._context.files_read,
                files_written=self._context.files_written,
                elapsed=elapsed,
            )

        return result
