"""Internationalization support for zhi.

Provides:
- LANGUAGE_PREAMBLE: injected into all skill system prompts so the LLM
  responds in the same language as the input document.
- t(key, **kwargs): translatable string lookup with en/zh catalogs.
- set_language(lang): configure the UI language ("auto", "en", "zh").
"""

from __future__ import annotations

import locale
import os
from typing import Any

# ---------------------------------------------------------------------------
# Language preamble — injected at prompt assembly time so every skill
# (including nested composition chains) respects the document language.
# ---------------------------------------------------------------------------

LANGUAGE_PREAMBLE = (
    "IMPORTANT: Always respond in the same language as the input document. "
    "If the document or user input is in Chinese, your ENTIRE output — "
    "including all section headers, table headers, column names, labels, "
    "and structural elements — MUST be in Chinese. "
    "Never mix languages in your response."
)

# ---------------------------------------------------------------------------
# UI string catalog
# ---------------------------------------------------------------------------

_current_language: str = "auto"


def set_language(lang: str) -> None:
    """Set the UI language. Accepts 'auto', 'en', or 'zh'."""
    global _current_language
    _current_language = lang


def get_language() -> str:
    """Return the current language setting (may be 'auto')."""
    return _current_language


def _get_system_locale() -> str | None:
    """Get system locale string, works on all platforms including Windows."""
    try:
        loc = locale.getlocale()[0]
        return loc
    except (ValueError, AttributeError):
        return None


def resolve_language() -> str:
    """Resolve 'auto' to a concrete language code ('en' or 'zh').

    Detection order:
    1. If language is explicitly set to 'en' or 'zh', use that.
    2. Check ZHI_LANGUAGE env var.
    3. Check LANG / LC_ALL env vars for 'zh' prefix.
    4. Check system locale via locale module (Windows fallback).
    5. Default to 'en'.
    """
    if _current_language not in ("auto", ""):
        return _current_language

    env_lang = os.environ.get("ZHI_LANGUAGE", "")
    if env_lang.startswith("zh"):
        return "zh"

    for var in ("LANG", "LC_ALL"):
        val = os.environ.get(var, "")
        if val.startswith("zh"):
            return "zh"

    # Fallback: check system locale (works on Windows where LANG is unset)
    sys_locale = _get_system_locale()
    if sys_locale and sys_locale.startswith("zh"):
        return "zh"

    return "en"


def prepend_preamble(system_prompt: str) -> str:
    """Prepend the language preamble to a skill system prompt."""
    return f"{LANGUAGE_PREAMBLE}\n\n{system_prompt}"


# ---------------------------------------------------------------------------
# String catalog: en + zh
# ---------------------------------------------------------------------------

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # -- Banner --
        "banner.tagline": "Terminal AI powered by Zhipu GLM",
        "banner.hint": "Type a message to chat, or /help for commands.",
        "banner.tagline_short": "Terminal AI \u00b7 Zhipu GLM",
        # -- REPL commands --
        "repl.help": (
            "Available commands:\n"
            "  /help              Show this help message\n"
            "  /auto              Switch to auto mode (skip tool confirmations, faster)\n"
            "  /approve           Switch to approve mode (confirm before tools, safer)\n"
            "  /model <name>      Switch model (glm-5, glm-4-flash, glm-4-air)\n"
            "  /think             Enable thinking mode\n"
            "  /fast              Disable thinking mode\n"
            "  /run <skill> [args]  Run a skill\n"
            "  /skill list        List available skills\n"
            "  /status            Show current session state\n"
            "  /reset             Clear conversation history\n"
            "  /undo              Remove last exchange\n"
            "  /usage             Show token/cost stats\n"
            "  /verbose           Toggle verbose output\n"
            "  /exit              Exit zhi\n"
            "\n"
            "Tip: End a line with \\ for multi-line input."
        ),
        "repl.unknown_cmd": "Unknown command: {command}. Type /help for available commands.",
        "repl.mode_auto": "Mode switched to auto",
        "repl.mode_approve": "Mode switched to approve",
        "repl.current_model": "Current model: {model}. Available: {available}",
        "repl.unknown_model": "Unknown model: {model}. Available: {available}",
        "repl.model_switched": "Model switched to {model}",
        "repl.think_on": "Thinking mode enabled",
        "repl.think_off": "Thinking mode disabled",
        "repl.goodbye": "Goodbye!",
        "repl.run_usage": "Usage: /run <skill> [files...]",
        "repl.unknown_skill": "Unknown skill '{skill}'. Available: {available}",
        "repl.interrupted": "\nInterrupted",
        "repl.skill_error": "Error running skill '{skill}': {error}",
        "repl.skill_max_turns": "Skill '{skill}' reached max turns without a final response.",
        "repl.no_skills": "No skills installed. Create one with /skill new",
        "repl.skill_list_title": "Available skills:",
        "repl.skill_new_todo": "Skill creation not yet implemented",
        "repl.skill_show_usage": "Usage: /skill show <name>",
        "repl.skill_edit_usage": "Usage: /skill edit <name>",
        "repl.skill_delete_usage": "Usage: /skill delete <name>",
        "repl.skill_usage": "Usage: /skill list|new|show|edit|delete <name>",
        "repl.skill_not_found": "Skill '{name}' not found",
        "repl.cleared": "Conversation cleared",
        "repl.nothing_undo": "Nothing to undo",
        "repl.undone": "Last exchange removed",
        "repl.verbose_on": "Verbose mode on",
        "repl.verbose_off": "Verbose mode off",
        "repl.status": "Model: {model} | Mode: {mode} | Thinking: {thinking} | Verbose: {verbose} | Turns: {turns} | Tokens: {tokens}",
        "repl.error_try_again": "Try again",
        "repl.error_check_connection": "Check your API key and connection",
        "repl.reset_confirm": "Clear entire conversation? [y/N]: ",
        "repl.on": "on",
        "repl.off": "off",
        "repl.max_turns": "Max turns reached without a final response",
        # -- Files --
        "files.extracting": "Extracting content from {count} file(s)...",
        "files.extracted": "Attached {count} file(s)",
        "files.not_found": "File not found: {path}",
        "files.unsupported": "Unsupported file type: {ext}",
        "files.extract_error": "Could not extract {path}: {error}",
        # -- UI --
        "ui.thinking": "Thinking...\n",
        "ui.error_label": "Error: {message}",
        "ui.reason_label": "Reason: {details}",
        "ui.try_label": "Try:",
        "ui.warning_title": "Warning",
        "ui.confirm_nocolor": "[CONFIRM] Allow {tool}({args})? [y/n]: ",
        "ui.confirm_rich": "Allow [bold]{tool}[/bold]({args})?",
        "ui.files_read": "{count} file{s} read",
        "ui.files_written": "{count} file{s} written",
        "ui.tool_done": "  done",
        "ui.thinking_prefix": "[thinking] ",
        "ui.done_fallback": "done",
        "ui.done_prefix": "Done: ",
        "ui.usage_nocolor": "[USAGE] Session: {tokens} tokens",
        "ui.session_used": "Session: ",
        "ui.tokens_suffix": " tokens",
        # -- Setup wizard --
        "setup.welcome": "Welcome to zhi (v{version})",
        "setup.intro": "Let's get you set up. This takes about 30 seconds.",
        "setup.step1": "Step 1/3: API Key",
        "setup.step1_prompt": "  Paste your Zhipu API key (get one at open.bigmodel.cn):",
        "setup.no_key": "  No API key provided. You can set it later with ZHI_API_KEY.",
        "setup.step2": "Step 2/3: Defaults",
        "setup.model_prompt": "  Default model for chat [glm-5]: ",
        "setup.skill_model_prompt": "  Default model for skills [glm-4-flash]: ",
        "setup.output_prompt": "  Output directory [zhi-output]: ",
        "setup.step3": "Step 3/3: Quick Demo",
        "setup.demo_prompt": "  Want to try a sample skill? [Y/n]: ",
        "setup.demo_skip": "  Demo skipped (not yet implemented).",
        "setup.language_prompt": "  Interface language [auto]: ",
        "setup.complete": "Setup complete. Type /help to see available commands.",
        # -- CLI --
        "cli.description": "Agentic CLI powered by Zhipu GLM models",
        "cli.version_help": "Show version and exit",
        "cli.command_help": "One-shot mode: send a single message and exit",
        "cli.setup_help": "Re-run the setup wizard",
        "cli.debug_help": "Enable debug logging",
        "cli.nocolor_help": "Disable colored output",
        "cli.language_help": "Interface language (auto, en, zh)",
        "cli.run_help": "Run a skill",
        "cli.skill_help": "Name of the skill to run",
        "cli.files_help": "Input files for the skill",
        "cli.no_api_key": "Error: No API key configured. Run `zhi --setup` first.",
        "cli.unknown_skill": "Error: Unknown skill '{skill}'. Available: {available}",
        "cli.no_stdin": "Error: No input received from stdin.",
    },
    "zh": {
        # -- Banner --
        "banner.tagline": "\u667a\u8c31 GLM \u9a71\u52a8\u7684\u7ec8\u7aef AI",
        "banner.hint": "\u8f93\u5165\u6d88\u606f\u5f00\u59cb\u5bf9\u8bdd\uff0c\u6216 /help \u67e5\u770b\u547d\u4ee4\u3002",
        "banner.tagline_short": "\u7ec8\u7aef AI \u00b7 \u667a\u8c31 GLM",
        # -- REPL commands --
        "repl.help": (
            "\u53ef\u7528\u547d\u4ee4\uff1a\n"
            "  /help              \u663e\u793a\u6b64\u5e2e\u52a9\u4fe1\u606f\n"
            "  /auto              \u5207\u6362\u5230\u81ea\u52a8\u6a21\u5f0f\uff08\u8df3\u8fc7\u5de5\u5177\u786e\u8ba4\uff0c\u66f4\u5feb\uff09\n"
            "  /approve           \u5207\u6362\u5230\u786e\u8ba4\u6a21\u5f0f\uff08\u5de5\u5177\u6267\u884c\u524d\u786e\u8ba4\uff0c\u66f4\u5b89\u5168\uff09\n"
            "  /model <\u540d\u79f0>      \u5207\u6362\u6a21\u578b (glm-5, glm-4-flash, glm-4-air)\n"
            "  /think             \u542f\u7528\u601d\u8003\u6a21\u5f0f\n"
            "  /fast              \u5173\u95ed\u601d\u8003\u6a21\u5f0f\n"
            "  /run <\u6280\u80fd> [\u6587\u4ef6]  \u8fd0\u884c\u6280\u80fd\n"
            "  /skill list        \u5217\u51fa\u53ef\u7528\u6280\u80fd\n"
            "  /status            \u663e\u793a\u5f53\u524d\u4f1a\u8bdd\u72b6\u6001\n"
            "  /reset             \u6e05\u9664\u5bf9\u8bdd\u5386\u53f2\n"
            "  /undo              \u64a4\u9500\u4e0a\u4e00\u8f6e\u5bf9\u8bdd\n"
            "  /usage             \u67e5\u770b token/\u8d39\u7528\u7edf\u8ba1\n"
            "  /verbose           \u5207\u6362\u8be6\u7ec6\u8f93\u51fa\n"
            "  /exit              \u9000\u51fa zhi\n"
            "\n"
            "\u63d0\u793a\uff1a\u884c\u672b\u8f93\u5165 \\ \u53ef\u6362\u884c\u7ee7\u7eed\u8f93\u5165\u3002"
        ),
        "repl.unknown_cmd": "\u672a\u77e5\u547d\u4ee4\uff1a{command}\u3002\u8f93\u5165 /help \u67e5\u770b\u53ef\u7528\u547d\u4ee4\u3002",
        "repl.mode_auto": "\u5df2\u5207\u6362\u5230\u81ea\u52a8\u6a21\u5f0f",
        "repl.mode_approve": "\u5df2\u5207\u6362\u5230\u786e\u8ba4\u6a21\u5f0f",
        "repl.current_model": "\u5f53\u524d\u6a21\u578b\uff1a{model}\u3002\u53ef\u7528\uff1a{available}",
        "repl.unknown_model": "\u672a\u77e5\u6a21\u578b\uff1a{model}\u3002\u53ef\u7528\uff1a{available}",
        "repl.model_switched": "\u5df2\u5207\u6362\u5230\u6a21\u578b {model}",
        "repl.think_on": "\u601d\u8003\u6a21\u5f0f\u5df2\u542f\u7528",
        "repl.think_off": "\u601d\u8003\u6a21\u5f0f\u5df2\u5173\u95ed",
        "repl.goodbye": "\u518d\u89c1\uff01",
        "repl.run_usage": "\u7528\u6cd5\uff1a/run <\u6280\u80fd> [\u6587\u4ef6...]",
        "repl.unknown_skill": "\u672a\u77e5\u6280\u80fd '{skill}'\u3002\u53ef\u7528\uff1a{available}",
        "repl.interrupted": "\n\u5df2\u4e2d\u65ad",
        "repl.skill_error": "\u8fd0\u884c\u6280\u80fd '{skill}' \u51fa\u9519\uff1a{error}",
        "repl.skill_max_turns": "\u6280\u80fd '{skill}' \u8fbe\u5230\u6700\u5927\u8f6e\u6570\uff0c\u672a\u83b7\u5f97\u6700\u7ec8\u54cd\u5e94\u3002",
        "repl.no_skills": "\u6ca1\u6709\u5df2\u5b89\u88c5\u7684\u6280\u80fd\u3002\u4f7f\u7528 /skill new \u521b\u5efa\u65b0\u6280\u80fd",
        "repl.skill_list_title": "\u53ef\u7528\u6280\u80fd\uff1a",
        "repl.skill_new_todo": "\u6280\u80fd\u521b\u5efa\u529f\u80fd\u5c1a\u672a\u5b9e\u73b0",
        "repl.skill_show_usage": "\u7528\u6cd5\uff1a/skill show <\u540d\u79f0>",
        "repl.skill_edit_usage": "\u7528\u6cd5\uff1a/skill edit <\u540d\u79f0>",
        "repl.skill_delete_usage": "\u7528\u6cd5\uff1a/skill delete <\u540d\u79f0>",
        "repl.skill_usage": "\u7528\u6cd5\uff1a/skill list|new|show|edit|delete <\u540d\u79f0>",
        "repl.skill_not_found": "\u6280\u80fd '{name}' \u672a\u627e\u5230",
        "repl.cleared": "\u5bf9\u8bdd\u5df2\u6e05\u9664",
        "repl.nothing_undo": "\u6ca1\u6709\u53ef\u64a4\u9500\u7684\u64cd\u4f5c",
        "repl.undone": "\u5df2\u79fb\u9664\u6700\u540e\u4e00\u8f6e\u5bf9\u8bdd",
        "repl.verbose_on": "\u8be6\u7ec6\u6a21\u5f0f \u5f00",
        "repl.verbose_off": "\u8be6\u7ec6\u6a21\u5f0f \u5173",
        "repl.status": "\u6a21\u578b\uff1a{model} | \u6a21\u5f0f\uff1a{mode} | \u601d\u8003\uff1a{thinking} | \u8be6\u7ec6\uff1a{verbose} | \u8f6e\u6b21\uff1a{turns} | Token\uff1a{tokens}",
        "repl.error_try_again": "\u8bf7\u91cd\u8bd5",
        "repl.error_check_connection": "\u8bf7\u68c0\u67e5 API \u5bc6\u94a5\u548c\u7f51\u7edc\u8fde\u63a5",
        "repl.reset_confirm": "\u6e05\u9664\u6574\u4e2a\u5bf9\u8bdd\uff1f[y/N]\uff1a",
        "repl.on": "\u5f00",
        "repl.off": "\u5173",
        "repl.max_turns": "\u5df2\u8fbe\u5230\u6700\u5927\u8f6e\u6570\uff0c\u672a\u83b7\u5f97\u6700\u7ec8\u54cd\u5e94",
        # -- Files --
        "files.extracting": "\u6b63\u5728\u63d0\u53d6 {count} \u4e2a\u6587\u4ef6\u7684\u5185\u5bb9...",
        "files.extracted": "\u5df2\u9644\u52a0 {count} \u4e2a\u6587\u4ef6",
        "files.not_found": "\u6587\u4ef6\u672a\u627e\u5230\uff1a{path}",
        "files.unsupported": "\u4e0d\u652f\u6301\u7684\u6587\u4ef6\u7c7b\u578b\uff1a{ext}",
        "files.extract_error": "\u65e0\u6cd5\u63d0\u53d6 {path} \u7684\u5185\u5bb9\uff1a{error}",
        # -- UI --
        "ui.thinking": "\u601d\u8003\u4e2d...\n",
        "ui.error_label": "\u9519\u8bef\uff1a{message}",
        "ui.reason_label": "\u539f\u56e0\uff1a{details}",
        "ui.try_label": "\u5efa\u8bae\uff1a",
        "ui.warning_title": "\u8b66\u544a",
        "ui.confirm_nocolor": "[\u786e\u8ba4] \u5141\u8bb8 {tool}({args})\uff1f[y/n]\uff1a",
        "ui.confirm_rich": "\u5141\u8bb8 [bold]{tool}[/bold]({args})\uff1f",
        "ui.files_read": "{count} \u4e2a\u6587\u4ef6\u5df2\u8bfb\u53d6",
        "ui.files_written": "{count} \u4e2a\u6587\u4ef6\u5df2\u5199\u5165",
        "ui.tool_done": "  \u5b8c\u6210",
        "ui.thinking_prefix": "[\u601d\u8003] ",
        "ui.done_fallback": "\u5b8c\u6210",
        "ui.done_prefix": "\u5b8c\u6210\uff1a",
        "ui.usage_nocolor": "[\u7edf\u8ba1] \u672c\u6b21\uff1a{tokens} \u4e2a token",
        "ui.session_used": "\u672c\u6b21\uff1a",
        "ui.tokens_suffix": " \u4e2a token",
        # -- Setup wizard --
        "setup.welcome": "\u6b22\u8fce\u4f7f\u7528 zhi (v{version})",
        "setup.intro": "\u8ba9\u6211\u4eec\u6765\u5b8c\u6210\u521d\u59cb\u8bbe\u7f6e\uff0c\u5927\u7ea6\u9700\u8981 30 \u79d2\u3002",
        "setup.step1": "\u7b2c 1/3 \u6b65\uff1aAPI \u5bc6\u94a5",
        "setup.step1_prompt": "  \u8bf7\u7c98\u8d34\u60a8\u7684\u667a\u8c31 API \u5bc6\u94a5\uff08\u5728 open.bigmodel.cn \u83b7\u53d6\uff09\uff1a",
        "setup.no_key": "  \u672a\u63d0\u4f9b API \u5bc6\u94a5\u3002\u60a8\u53ef\u4ee5\u7a0d\u540e\u901a\u8fc7 ZHI_API_KEY \u8bbe\u7f6e\u3002",
        "setup.step2": "\u7b2c 2/3 \u6b65\uff1a\u9ed8\u8ba4\u914d\u7f6e",
        "setup.model_prompt": "  \u5bf9\u8bdd\u9ed8\u8ba4\u6a21\u578b [glm-5]\uff1a",
        "setup.skill_model_prompt": "  \u6280\u80fd\u9ed8\u8ba4\u6a21\u578b [glm-4-flash]\uff1a",
        "setup.output_prompt": "  \u8f93\u51fa\u76ee\u5f55 [zhi-output]\uff1a",
        "setup.step3": "\u7b2c 3/3 \u6b65\uff1a\u5feb\u901f\u6f14\u793a",
        "setup.demo_prompt": "  \u8981\u5c1d\u8bd5\u793a\u4f8b\u6280\u80fd\u5417\uff1f[Y/n]\uff1a",
        "setup.demo_skip": "  \u6f14\u793a\u5df2\u8df3\u8fc7\uff08\u5c1a\u672a\u5b9e\u73b0\uff09\u3002",
        "setup.language_prompt": "  \u754c\u9762\u8bed\u8a00 [auto]\uff1a",
        "setup.complete": "\u8bbe\u7f6e\u5b8c\u6210\u3002\u8f93\u5165 /help \u67e5\u770b\u53ef\u7528\u547d\u4ee4\u3002",
        # -- CLI --
        "cli.description": "\u57fa\u4e8e\u667a\u8c31 GLM \u7684\u667a\u80fd\u7ec8\u7aef AI",
        "cli.version_help": "\u663e\u793a\u7248\u672c\u5e76\u9000\u51fa",
        "cli.command_help": "\u5355\u6b21\u6a21\u5f0f\uff1a\u53d1\u9001\u4e00\u6761\u6d88\u606f\u540e\u9000\u51fa",
        "cli.setup_help": "\u91cd\u65b0\u8fd0\u884c\u8bbe\u7f6e\u5411\u5bfc",
        "cli.debug_help": "\u542f\u7528\u8c03\u8bd5\u65e5\u5fd7",
        "cli.nocolor_help": "\u7981\u7528\u5f69\u8272\u8f93\u51fa",
        "cli.language_help": "\u754c\u9762\u8bed\u8a00 (auto, en, zh)",
        "cli.run_help": "\u8fd0\u884c\u6280\u80fd",
        "cli.skill_help": "\u6280\u80fd\u540d\u79f0",
        "cli.files_help": "\u6280\u80fd\u8f93\u5165\u6587\u4ef6",
        "cli.no_api_key": "\u9519\u8bef\uff1a\u672a\u914d\u7f6e API \u5bc6\u94a5\u3002\u8bf7\u5148\u8fd0\u884c `zhi --setup`\u3002",
        "cli.unknown_skill": "\u9519\u8bef\uff1a\u672a\u77e5\u6280\u80fd '{skill}'\u3002\u53ef\u7528\uff1a{available}",
        "cli.no_stdin": "\u9519\u8bef\uff1a\u672a\u4ece\u6807\u51c6\u8f93\u5165\u63a5\u6536\u5230\u5185\u5bb9\u3002",
    },
}


def t(key: str, **kwargs: Any) -> str:
    """Look up a translatable string by key.

    Falls back to English if the key is missing in the current language,
    and falls back to the raw key if missing entirely.
    """
    lang = resolve_language()
    strings = _STRINGS.get(lang, _STRINGS["en"])
    template = strings.get(key, _STRINGS["en"].get(key, key))
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
