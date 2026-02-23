"""Interactive REPL loop with slash commands, history, and tab completion.

Uses prompt_toolkit for input with persistent history, tab completion,
multi-line input, and CJK/IME support.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import platformdirs
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory, InMemoryHistory

from zhi.agent import Context, PermissionMode, Role
from zhi.agent import run as agent_run
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
    "/reset",
    "/undo",
    "/usage",
    "/verbose",
]

_MAX_HISTORY_ENTRIES = 10_000


class _FilteredFileHistory(FileHistory):
    """File history that excludes lines containing sensitive patterns."""

    def store_string(self, string: str) -> None:
        if _SENSITIVE_PATTERNS.search(string):
            return
        super().store_string(string)


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

        # Set up tab completion
        completions = list(_SLASH_COMMANDS)
        completions.extend(MODELS.keys())
        self._completer = WordCompleter(completions, sentence=True)

        self._session: PromptSession[str] = PromptSession(
            history=self._history,
            completer=self._completer,
        )

    def _get_prompt(self) -> str:
        """Get the prompt string with mode indicator."""
        mode = self._context.permission_mode.value
        return f"You [{mode}]: "

    def run(self) -> None:
        """Run the REPL loop until /exit or Ctrl+D."""
        self._running = True
        self._ui.print("Welcome to zhi. Type /help for commands.")

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
            "/reset": self._handle_reset,
            "/undo": self._handle_undo,
            "/usage": self._handle_usage,
            "/verbose": self._handle_verbose,
        }

        handler = handlers.get(command)
        if handler is None:
            msg = f"Unknown command: {command}. Type /help for available commands."
            self._ui.print(msg)
            return msg

        return handler(args)

    def _handle_help(self, _args: str = "") -> str:
        """Show available commands."""
        help_text = """Available commands:
  /help              Show this help message
  /auto              Switch to auto mode (no permission prompts)
  /approve           Switch to approve mode (default)
  /model <name>      Switch model (glm-5, glm-4-flash, glm-4-air)
  /think             Enable thinking mode
  /fast              Disable thinking mode
  /run <skill> [args]  Run a skill
  /skill list|new|show|edit|delete  Manage skills
  /reset             Clear conversation history
  /undo              Remove last exchange
  /usage             Show token/cost stats
  /verbose           Toggle verbose output
  /exit              Exit zhi"""
        self._ui.print(help_text)
        return help_text

    def _handle_auto(self, _args: str = "") -> str:
        """Switch to auto mode."""
        self._context.permission_mode = PermissionMode.AUTO
        msg = "Mode switched to auto"
        self._ui.print(msg)
        return msg

    def _handle_approve(self, _args: str = "") -> str:
        """Switch to approve mode."""
        self._context.permission_mode = PermissionMode.APPROVE
        msg = "Mode switched to approve"
        self._ui.print(msg)
        return msg

    def _handle_model(self, args: str = "") -> str:
        """Switch the model for the current session."""
        model_name = args.strip()
        if not model_name:
            available = ", ".join(MODELS.keys())
            msg = f"Current model: {self._context.model}. Available: {available}"
            self._ui.print(msg)
            return msg

        if not is_valid_model(model_name):
            msg = f"Unknown model: {model_name}. Available: {', '.join(MODELS.keys())}"
            self._ui.print(msg)
            return msg

        self._context.model = model_name
        msg = f"Model switched to {model_name}"
        self._ui.print(msg)
        return msg

    def _handle_think(self, _args: str = "") -> str:
        """Enable thinking mode."""
        self._context.thinking_enabled = True
        msg = "Thinking mode enabled"
        self._ui.print(msg)
        return msg

    def _handle_fast(self, _args: str = "") -> str:
        """Disable thinking mode."""
        self._context.thinking_enabled = False
        msg = "Thinking mode disabled"
        self._ui.print(msg)
        return msg

    def _handle_exit(self, _args: str = "") -> str:
        """Exit the REPL."""
        self._running = False
        if self._context.session_tokens > 0:
            self._ui.show_usage(self._context.session_tokens, 0.0)
        msg = "Goodbye!"
        self._ui.print(msg)
        return msg

    def _handle_run(self, args: str = "") -> str:
        """Run a skill by name with optional file arguments."""
        if not args.strip():
            msg = "Usage: /run <skill> [files...]"
            self._ui.print(msg)
            return msg

        from zhi.skills import discover_skills

        parts = args.strip().split()
        skill_name = parts[0]
        files = parts[1:]

        skills = discover_skills()
        if skill_name not in skills:
            available = ", ".join(sorted(skills.keys())) if skills else "(none)"
            msg = f"Unknown skill '{skill_name}'. Available: {available}"
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
                    "content": skill.system_prompt,
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
            on_permission=lambda tool, call: self._ui.ask_permission(tool.name, {}),
        )

        try:
            result = agent_run(skill_context)
        except KeyboardInterrupt:
            self._ui.print("\nInterrupted")
            return "Interrupted"
        except Exception as e:
            logger.exception("Skill run error")
            msg = f"Error running skill '{skill_name}': {e}"
            self._ui.print(msg)
            return msg

        if result is None:
            msg = f"Skill '{skill_name}' reached max turns without a final response."
            self._ui.show_warning(msg)
            return msg

        self._ui.stream_end()
        return result

    def _handle_skill(self, args: str = "") -> str:
        """Handle /skill subcommands."""
        parts = args.strip().split(maxsplit=1)
        subcommand = parts[0] if parts else ""

        if subcommand == "list":
            from zhi.skills import discover_skills

            skills = discover_skills()
            if not skills:
                msg = "No skills installed. Create one with /skill new"
                self._ui.print(msg)
                return msg
            lines = ["Available skills:"]
            for name, cfg in sorted(skills.items()):
                source_tag = f" ({cfg.source})" if cfg.source else ""
                lines.append(f"  {name}{source_tag} — {cfg.description}")
            msg = "\n".join(lines)
            self._ui.print(msg)
            return msg
        elif subcommand == "new":
            msg = "Skill creation not yet implemented"
            self._ui.print(msg)
            return msg
        elif subcommand == "show":
            name = parts[1] if len(parts) > 1 else ""
            if not name:
                msg = "Usage: /skill show <name>"
                self._ui.print(msg)
                return msg
            msg = f"Skill '{name}' not found"
            self._ui.print(msg)
            return msg
        elif subcommand == "edit":
            name = parts[1] if len(parts) > 1 else ""
            if not name:
                msg = "Usage: /skill edit <name>"
                self._ui.print(msg)
                return msg
            msg = f"Skill '{name}' not found"
            self._ui.print(msg)
            return msg
        elif subcommand == "delete":
            name = parts[1] if len(parts) > 1 else ""
            if not name:
                msg = "Usage: /skill delete <name>"
                self._ui.print(msg)
                return msg
            msg = f"Skill '{name}' not found"
            self._ui.print(msg)
            return msg
        else:
            msg = "Usage: /skill list|new|show|edit|delete <name>"
            self._ui.print(msg)
            return msg

    def _handle_reset(self, _args: str = "") -> str:
        """Clear conversation history."""
        # Keep system messages
        self._context.conversation = [
            msg
            for msg in self._context.conversation
            if msg.get("role") == Role.SYSTEM.value
        ]
        msg = "Conversation cleared"
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
            msg = "Nothing to undo"
            self._ui.print(msg)
            return msg

        self._context.conversation = conv[:last_user_idx]
        msg = "Last exchange removed"
        self._ui.print(msg)
        return msg

    def _handle_usage(self, _args: str = "") -> str:
        """Show token/cost stats."""
        tokens = self._context.session_tokens
        # Rough cost estimate
        cost = tokens * 0.00001  # placeholder
        self._ui.show_usage(tokens, cost)
        msg = f"Tokens: {tokens}, Cost: ~${cost:.4f}"
        return msg

    def _handle_verbose(self, _args: str = "") -> str:
        """Toggle verbose output."""
        self._ui.verbose = not self._ui.verbose
        state = "on" if self._ui.verbose else "off"
        msg = f"Verbose mode {state}"
        self._ui.print(msg)
        return msg

    def _handle_chat(self, text: str) -> str | None:
        """Send user text to the agent and display results."""
        # Add user message to conversation
        self._context.conversation.append(
            {
                "role": Role.USER.value,
                "content": text,
            }
        )

        try:
            result = agent_run(self._context)
        except KeyboardInterrupt:
            self._ui.print("\nInterrupted")
            return None
        except Exception as e:
            logger.exception("Agent error")
            from zhi.errors import ApiError

            self._ui.show_error(
                ApiError(
                    str(e),
                    suggestions=["Try again", "Check your API key and connection"],
                )
            )
            return None

        if result is None:
            self._ui.show_warning("Max turns reached without a final response")

        return result
