# zhi

An agentic CLI powered by Zhipu GLM models. Create and run custom AI skills from your terminal.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests: passing](https://img.shields.io/badge/tests-298%20passing-brightgreen)

## What is zhi?

`zhi` is an open-source Python CLI that gives you an AI-powered assistant in your terminal. It uses a **two-model architecture** to balance quality and cost:

- **Interactive chat** uses GLM-5 for complex reasoning, skill creation, and open-ended conversation
- **Skill execution** uses GLM-4-flash for running predefined workflows at less than 10% of the cost

Install with `pip install zhi`, set your Zhipu API key, and start working. First useful output in under 60 seconds.

## Install

```bash
pip install zhi
```

For optional Excel and Word file support:

```bash
pip install "zhi[all]"
```

Requires Python 3.10 or higher.

## Quickstart

Set your Zhipu API key:

```bash
export ZHI_API_KEY=sk-...
```

Or run the guided setup wizard:

```bash
zhi --setup
```

Then start the REPL:

```
$ zhi
Welcome to zhi. Type /help for commands.

You [approve]: Summarize the key points of report.pdf
zhi: [reading report.pdf via OCR...]
zhi: Here are the key points from the report...

You [approve]: /auto
Mode switched to auto

You [auto]: Write a CSV of the quarterly revenue figures
zhi: File written: quarterly-revenue.csv (1.2KB)
```

## CLI Usage

```
zhi                          # Interactive REPL
zhi -c "your message"        # One-shot mode: send a message and exit
zhi run <skill> [files...]   # Run a skill on input files
zhi --setup                  # Run the setup wizard
zhi --version                # Show version
zhi --debug                  # Enable debug logging
zhi --no-color               # Disable colored output
```

## Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/auto` | Switch to auto mode (no permission prompts for safe tools) |
| `/approve` | Switch to approve mode (confirm risky actions) |
| `/model <name>` | Switch model (glm-5, glm-4-flash, glm-4-air) |
| `/think` | Enable thinking mode |
| `/fast` | Disable thinking mode |
| `/run <skill> [args]` | Run a skill |
| `/skill list` | List installed skills |
| `/skill new` | Create a new skill |
| `/skill show <name>` | Show skill details |
| `/skill edit <name>` | Edit a skill |
| `/skill delete <name>` | Delete a skill (only removes zhi's own YAML files) |
| `/reset` | Clear conversation history |
| `/undo` | Remove last exchange |
| `/usage` | Show token and cost stats |
| `/verbose` | Toggle verbose output |
| `/exit` | Exit zhi |

## Built-in Tools

The agent can use these tools during conversation:

| Tool | Description | Risky |
|------|-------------|-------|
| `file_read` | Read text files within the working directory (max 100KB) | No |
| `file_write` | Write new files to `zhi-output/` (.md, .txt, .json, .csv, .xlsx, .docx) | Yes |
| `file_list` | List directory contents with size and modification date | No |
| `ocr` | Extract text from images and PDFs (PNG, JPG, PDF, GIF, WEBP; max 20MB) | No |
| `shell` | Run shell commands (always requires confirmation) | Yes |
| `web_fetch` | Fetch and extract text from a URL | No |
| `skill_create` | Create a new skill YAML configuration | Yes |

Risky tools require user confirmation in approve mode.

## Skills

Skills are reusable AI workflows defined as YAML configuration files. They specify a system prompt, which tools to use, and what model to run on.

### Built-in skills

- **summarize** -- Summarize a text file or document
- **translate** -- Translate text between languages (defaults to Chinese)

### Example skill YAML

```yaml
name: summarize
description: Summarize a text file or document
model: glm-4-flash
system_prompt: |
  You are a concise summarization assistant. Read the provided text
  and produce a clear, well-structured summary.
tools:
  - file_read
  - file_write
max_turns: 5
input:
  description: A text file to summarize
  args:
    - name: file
      type: file
      required: true
output:
  description: Markdown summary
  directory: zhi-output
```

### Creating skills

Use `/skill new` in the REPL to create a skill interactively, or write a YAML file directly in your skills directory.

Skills are stored in the platform-specific config directory under `skills/`.

## File Safety

`zhi` enforces strict safety constraints:

- **No file deletion** -- there is no delete tool
- **No file modification** -- `file_write` creates new files only; it cannot overwrite existing files
- **Scoped output** -- all writes go to `./zhi-output/`; path traversal (`..`) is rejected
- **Shell always confirms** -- every shell command requires explicit `y/n` confirmation, even in auto mode
- **Destructive command warnings** -- commands like `rm`, `mv`, `del` trigger extra warnings
- **Catastrophic patterns blocked** -- patterns like `rm -rf /` are blocklisted outright

## Configuration

### Config file

Configuration is stored as YAML in your platform-specific config directory:

- **macOS**: `~/Library/Application Support/zhi/config.yaml`
- **Windows**: `%APPDATA%\zhi\config.yaml`
- **Linux**: `~/.config/zhi/config.yaml`

### Environment variables

Environment variables override config file values:

| Variable | Description | Default |
|----------|-------------|---------|
| `ZHI_API_KEY` | Zhipu API key (required) | -- |
| `ZHI_DEFAULT_MODEL` | Default chat model | `glm-5` |
| `ZHI_OUTPUT_DIR` | Output directory for file writes | `zhi-output` |
| `ZHI_LOG_LEVEL` | Logging level | `INFO` |
| `NO_COLOR` | Disable colored output (any value) | -- |

## Development

```bash
git clone https://github.com/chan-kinghin/zhicli.git
cd zhicli
pip install -e ".[dev,all]"

# Run tests
pytest tests/ -v

# Lint and format
ruff check src/zhi/
ruff format src/zhi/

# Type check
mypy --strict src/zhi/

# Coverage
pytest --cov=zhi --cov-report=term-missing
```

## License

MIT
