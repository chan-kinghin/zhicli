"""Interactive REPL loop with slash commands, history, and tab completion.

Uses prompt_toolkit for input with persistent history, tab completion,
multi-line input, and CJK/IME support.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

import platformdirs
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory, InMemoryHistory

from zhi.agent import Context, PermissionMode, Role, safe_parse_args
from zhi.agent import run as agent_run
from zhi.i18n import prepend_preamble, t
from zhi.models import MODELS, is_valid_model
from zhi.ui import UI

logger = logging.getLogger(__name__)

# Lines matching these patterns are excluded from history
_SENSITIVE_PATTERNS = re.compile(r"(api_key|password|token|secret)", re.IGNORECASE)

_SLASH_COMMANDS = [
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
]

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
            prefix = text[5:]
            for name in sorted(self._skills_fn()):
                if name.startswith(prefix):
                    yield Completion(name, start_position=-len(prefix))
        elif text.startswith("/model "):
            prefix = text[7:]
            for name in self._models:
                if name.startswith(prefix):
                    yield Completion(name, start_position=-len(prefix))
        elif text.startswith("/skill "):
            prefix = text[7:]
            for sub in ["list", "show", "edit", "delete"]:
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

        self._session: PromptSession[str] = PromptSession(
            history=self._history,
            completer=self._completer,
        )

    def _get_prompt(self) -> str:
        """Get the prompt string."""
        return "zhi> "

    def run(self) -> None:
        """Run the REPL loop until /exit or Ctrl+D."""
        self._running = True
        from zhi import __version__

        self._ui.show_banner(__version__)

        while self._running:
            try:
                user_input = self._session.prompt(self._get_prompt())
            except KeyboardInterrupt:
                # Ctrl+C: cancel current input, return to prompt
                continue
            except EOFError:
                # Ctrl+D: exit gracefully
                self._handle_exit()
                break

            user_input = self._handle_continuation(user_input)

            if not user_input.strip():
                continue

            self.handle_input(user_input.strip())

    def _handle_continuation(self, text: str) -> str:
        """Handle multi-line input with backslash continuation."""
        while text.endswith("\\"):
            text = text[:-1]  # Remove trailing backslash
            try:
                continuation = self._session.prompt("...  ")
                text += "\n" + continuation
            except (KeyboardInterrupt, EOFError):
                break
        return text

    def handle_input(self, text: str) -> str | None:
        """Handle user input: dispatch slash commands or send to agent.

        Returns the command result message (for testing), or None.
        """
        if text.startswith("/"):
            return self._handle_command(text)
        return self._handle_chat(text)

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

        parts = args.strip().split()
        skill_name = parts[0]
        files = parts[1:]

        skills = self._skills_cache.get()
        if skill_name not in skills:
            available = ", ".join(sorted(skills.keys())) if skills else "(none)"
            msg = t("repl.unknown_skill", skill=skill_name, available=available)
            self._ui.print(msg)
            return msg

        skill = skills[skill_name]

        user_content = f"Run the '{skill_name}' skill."
        if files:
            file_list = ", ".join(files)
            user_content += f" Input files: {file_list}"

        # Build a skill-scoped context from the current context's client
        from zhi.tools import ToolRegistry, register_skill_tools

        skill_registry = ToolRegistry()
        # Register base tools the skill needs
        for tool_name in skill.tools:
            existing = self._context.tools.get(tool_name)
            if existing is not None:
                skill_registry.register(existing)

        # Also register skill-tools for composition
        register_skill_tools(skill_registry, skills, self._context.client)

        skill_tools = skill_registry.filter_by_names(skill.tools)
        # Also include skill_ prefixed versions
        for t_name in skill.tools:
            prefixed = f"skill_{t_name}"
            st = skill_registry.get(prefixed)
            if st is not None:
                skill_tools[prefixed] = st

        skill_schemas = [t.to_function_schema() for t in skill_tools.values()]

        conversation: list[dict[str, Any]] = []
        if skill.system_prompt:
            conversation.append(
                {
                    "role": Role.SYSTEM.value,
                    "content": prepend_preamble(skill.system_prompt),
                }
            )
        conversation.append({"role": Role.USER.value, "content": user_content})

        skill_context = Context(
            config=self._context.config,
            client=self._context.client,
            model=skill.model,
            tools=skill_tools,
            tool_schemas=skill_schemas,
            permission_mode=self._context.permission_mode,
            conversation=conversation,
            max_turns=skill.max_turns,
            on_stream=self._ui.stream,
            on_thinking=self._ui.show_thinking,
            on_tool_start=self._ui.show_tool_start,
            on_tool_end=self._ui.show_tool_end,
            on_permission=lambda tool, call: self._ui.ask_permission(
                tool.name,
                safe_parse_args(call["function"]["arguments"]),
            ),
            on_waiting=self._ui.show_waiting,
            on_waiting_done=self._ui.clear_waiting,
        )

        try:
            result = agent_run(skill_context)
        except KeyboardInterrupt:
            self._ui.print(t("repl.interrupted"))
            return "Interrupted"
        except Exception as e:
            logger.exception("Skill run error")
            msg = t("repl.skill_error", skill=skill_name, error=str(e))
            self._ui.print(msg)
            return msg
        finally:
            # Merge skill token usage back into the main session
            self._context.session_tokens += skill_context.session_tokens

        if result is None:
            msg = t("repl.skill_max_turns", skill=skill_name)
            self._ui.show_warning(msg)
            return msg

        self._ui.stream_end()
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
            msg = "Editing skills is not yet supported. Edit the YAML file directly."
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
            msg = "Deleting skills is not yet supported."
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

    def _handle_chat(self, text: str) -> str | None:
        """Send user text to the agent and display results."""
        # Add user message to conversation
        user_msg = {
            "role": Role.USER.value,
            "content": text,
        }
        self._context.conversation.append(user_msg)

        try:
            result = agent_run(self._context)
        except KeyboardInterrupt:
            self._ui.print(t("repl.interrupted"))
            return None
        except Exception as e:
            logger.exception("Agent error")
            # Remove the user message to avoid consecutive user messages
            # in conversation (which would confuse the LLM on next turn)
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

        if result is None:
            self._ui.show_warning(t("repl.max_turns"))
        else:
            self._ui.stream_end()

        return result
