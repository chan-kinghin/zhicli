# CLI Reference

## Command Line Usage

```
zhi                        # Interactive REPL
zhi -c "message"           # Single message mode
zhi run <skill> [files]    # Run a skill
zhi --setup                # Configuration wizard
zhi --version              # Show version
zhi --debug                # Enable debug logging
zhi --no-color             # Disable color output
zhi --language <LANG>      # Set interface language (auto, en, zh)
```

## Modes

### Interactive REPL

Launch the REPL by running `zhi` with no arguments:

```bash
zhi
```

Features:

- Persistent command history (saved to `~/.config/zhi/history.txt`)
- Tab completion for slash commands, model names, and skill names
- Multi-line input with `\` continuation
- CJK/IME input support via prompt_toolkit
- Sensitive inputs (containing `api_key`, `password`, `token`, `secret`) are excluded from history

### Single Message Mode

Send a single message and exit:

```bash
zhi -c "What files are in the current directory?"
```

### Skill Run Mode

Run a named skill with optional input files:

```bash
zhi run summarize report.txt
zhi run compare v1.md v2.md
zhi run extract-table invoices/receipt.pdf
```

### Pipe Mode

Pipe text from stdin:

```bash
echo "translate this to Chinese" | zhi
cat document.txt | zhi -c "summarize this"
git log --oneline -20 | zhi -c "summarize recent changes"
```

!!! info "Pipe detection"
    zhi automatically detects when stdin is not a terminal and reads from it.

---

## Slash Commands

The REPL supports 14 slash commands for controlling the session:

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show available commands and tips | `/help` |
| `/auto` | Switch to auto mode (skip tool confirmations) | `/auto` |
| `/approve` | Switch to approve mode (confirm before risky tools) | `/approve` |
| `/model <name>` | Switch the LLM model for the session | `/model glm-4-flash` |
| `/think` | Enable thinking mode (extended reasoning) | `/think` |
| `/fast` | Disable thinking mode (faster responses) | `/fast` |
| `/run <skill> [files]` | Run a skill with optional file arguments | `/run summarize report.txt` |
| `/skill list` | List all available skills | `/skill list` |
| `/skill show <name>` | Show details of a specific skill | `/skill show analyze` |
| `/status` | Show current session state | `/status` |
| `/reset` | Clear conversation history (with confirmation) | `/reset` |
| `/undo` | Remove the last user message and AI response | `/undo` |
| `/usage` | Show token usage statistics | `/usage` |
| `/verbose` | Toggle verbose output | `/verbose` |
| `/exit` | Exit zhi (shows usage stats if any) | `/exit` |

### Permission Modes

| Mode | Behavior | Switch command |
|------|----------|---------------|
| **approve** (default) | Confirm before executing risky tools (`file_write`, `shell`, `skill_create`) | `/approve` |
| **auto** | Skip confirmation for risky tools (shell still always confirms) | `/auto` |

!!! warning "Shell always confirms"
    The `shell` tool requires confirmation regardless of permission mode. This is a safety measure that cannot be bypassed.

### Model Switching

Available models:

| Model | Tier | Thinking | Tools |
|-------|------|----------|-------|
| `glm-5` | Premium | Yes | Yes |
| `glm-4-flash` | Economy | No | Yes |
| `glm-4-air` | Economy | No | Yes |

```
zhi> /model glm-4-flash
Model switched to glm-4-flash
```

### Status Display

```
zhi> /status
Model: glm-5 | Mode: approve | Thinking: on | Verbose: off | Turns: 3 | Tokens: 1523
```

---

## Global Options

| Option | Description |
|--------|-------------|
| `--version` | Print version and exit |
| `--setup` | Run the first-time configuration wizard |
| `--debug` | Set logging to DEBUG level (shows API calls, tool execution details) |
| `--no-color` | Disable Rich formatting and colors (also respects `NO_COLOR` env var) |
| `--language LANG` | Set interface language (`auto`, `en`, `zh`). Overrides config file setting. |
| `-c MESSAGE` | One-shot mode: send a single message, print the response, and exit |

---

## Exit

Exit the REPL using any of:

- `/exit` command
- `Ctrl+D` (EOF)
- `Ctrl+C` cancels current input but does not exit

On exit, zhi displays session token usage if any tokens were consumed.
