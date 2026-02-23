# Improved Plan: `zhi` -- Agentic CLI powered by Zhipu GLM

> Version: 2.0 (synthesized from original plan + architecture audit + test strategy + success metrics + UX improvements)
> Date: 2026-02-23

---

## Table of Contents

1. [Context & Vision](#1-context--vision)
2. [User Experience](#2-user-experience)
3. [Architecture](#3-architecture)
4. [Key Design Decisions](#4-key-design-decisions)
5. [Architecture Improvements](#5-architecture-improvements)
6. [Implementation Stages (34 Tasks)](#6-implementation-stages-34-tasks)
7. [Gaps & Risks](#7-gaps--risks)
8. [CI/CD & Quality](#8-cicd--quality)
9. [Metrics & Telemetry](#9-metrics--telemetry)
10. [Post-v1 Roadmap](#10-post-v1-roadmap)

---

## 1. Context & Vision

Build an open-source Python CLI called `zhi`. Users install with `pip install zhi`, set their Zhipu API key, and get an agentic assistant that can create and run custom skills. Cross-platform: macOS + Windows.

**Core insight -- two-model architecture:**
- **Skill creation**: GLM-5 (smart, agentic) helps the user design a skill interactively. One-time cost.
- **Skill execution**: cheap model (GLM-4-flash) follows the skill's recipe with tool calling. Daily use, nearly free.

**Target**: Skill execution on GLM-4-flash costs < 10% of the equivalent GLM-5 execution, making daily use nearly free.

**Design Principles** (guide all UX decisions):
1. **Instant value** -- First run to first useful output in under 60 seconds.
2. **Progressive disclosure** -- Start simple; discover advanced features as needed.
3. **Transparency over magic** -- Always show what the agent is doing (tool, file, model).
4. **Fail helpfully** -- Every error tells the user what to do next. No dead ends.
5. **Respect the terminal** -- Work with terminal conventions (Ctrl+C, Up for history, Tab to complete).
6. **Chinese-first internationalization** -- CJK text rendering, IME input, and Chinese-language support are first-class.
7. **Scriptable by default** -- Everything in the REPL also works non-interactively.

---

## 2. User Experience

### 2.1 First-Run Onboarding

A 3-step wizard runs on first launch:

```
$ zhi
Welcome to zhi (v0.1.0)

Let's get you set up. This takes about 30 seconds.

Step 1/3: API Key
  Paste your Zhipu API key (get one at open.bigmodel.cn):
  > sk-***************

  Validating... connected (GLM-5 available)

Step 2/3: Defaults
  Default model for chat: [GLM-5] (press Enter to accept)
  Default model for skills: [GLM-4-flash] (press Enter to accept)
  Output directory: [./zhi-output] (press Enter to accept)

Step 3/3: Quick Demo
  Want to try a sample skill? [Y/n]: y
  Running "summarize" on a sample text...
  Done! Your summary is at ./zhi-output/sample-summary.md

Setup complete. Type /help to see available commands.
You:
```

Key rules:
- API key validation is immediate (lightweight model-listing call). Shows available models.
- Invalid key gets a clear message ("Keys start with `sk-`. Regenerate at open.bigmodel.cn.").
- Store key in `~/.zhi/config.yaml` with file permissions 600 (owner-only).
- `ZHI_API_KEY` env var overrides config file.
- Wizard only runs once. Re-run with `zhi --setup` or `zhi config reset`.
- If demo fails (network issue), show friendly message and continue. Do not block onboarding.

### 2.2 Interactive REPL

```
$ zhi
Welcome to zhi. Type /help for commands.

You: Compare these two reports and give me an Excel summary
[drag files or type paths: report_v1.pdf report_v2.pdf]

Thinking...
  These are PDF invoices, I need to OCR them first, then compare content.

[1/3] OCR: report_v1.pdf (2,340 chars)
[2/3] OCR: report_v2.pdf (2,518 chars)
[3/3] Writing comparison.xlsx
       Allow? [y/n]: y

Done: 2 files read, 1 file written (4.1s)
  -> zhi-output/comparison.xlsx (12KB)

You: /auto
  Mode switched to auto

You: Now translate that comparison to Chinese
zhi: Writing comparison_zh.xlsx
     Done

You: I want to create a skill for this
zhi: I'll create a "compare-to-excel" skill:
     Name: compare-to-excel
     Input: Two file paths
     Output: Excel comparison report
     Tools: file_read, ocr, file_write
     Save? [y/n]: y
     Saved. Run with: /run compare-to-excel <file1> <file2>

You: /run compare-to-excel invoice_jan.pdf invoice_feb.pdf
Running compare-to-excel (glm-4-flash)...
     OCR -> Write zhi-output/comparison.xlsx
     Done

You: /exit
Session used 4,320 tokens (~$0.03)
```

### 2.3 Slash Commands

| Command | Action |
|---------|--------|
| `/run <skill> [files]` | Run a skill (uses skill's cheap model) |
| `/skill list` | List all available skills |
| `/skill new` | Interactively create a new skill |
| `/skill show <name>` | Display skill YAML with syntax highlighting |
| `/skill edit <name>` | Open skill YAML in `$EDITOR` |
| `/skill delete <name>` | Delete a skill (with confirmation) |
| `/auto` | Switch to auto mode -- no permission prompts |
| `/approve` | Switch to approve mode (default) |
| `/think` | Enable GLM-5 thinking mode (default) |
| `/fast` | Disable thinking -- faster responses |
| `/model <name>` | Switch model for current session |
| `/reset` | Clear conversation, keep config |
| `/undo` | Remove last exchange (user msg + AI response) |
| `/usage` | Show token/cost stats for current session |
| `/verbose` | Toggle verbose output |
| `/help` | Show available commands |
| `/exit` | Exit zhi |

Everything else typed is sent to the AI as a message.

### 2.4 REPL Input Features

- **Persistent history**: saved to `~/.zhi/history.txt` (max 10,000 entries). Up/Down navigation, Ctrl+R search. Excludes lines containing `api_key`, `password`, `token`, `secret`.
- **Tab completion**: slash commands, skill names after `/run`, model names after `/model`, file paths when input contains `/` or `./`.
- **Multi-line input**: backslash `\` at EOL continues. Prompt changes from `You: ` to `...  `.
- **File path autocomplete**: via `prompt_toolkit` PathCompleter. Drag-and-drop from terminal works natively.
- **CJK/IME input**: `prompt_toolkit` handles CJK input correctly. Explicitly tested for Chinese.

### 2.5 Thinking Mode

GLM-5's thinking mode is enabled by default in interactive chat. The model reasons before acting, rendered in dim/italic:

```
Thinking...
  These are PDF invoices, I'll need to OCR them first.
  Then compare line items and output differences as Excel.
```

- `/think` -- enable (default for interactive)
- `/fast` -- disable (for quick answers, or when using a cheaper model)
- Skill execution (`/run`) has thinking OFF by default (cheap model, follows recipe)

### 2.6 Permission Modes

| Mode | Behavior |
|------|----------|
| **Approve** (default) | Asks before risky actions (file write, shell) |
| **Auto** | Executes everything, just logs what's happening |

Mode indicator shown in prompt: `You [approve]: ` vs `You [auto]: `.

### 2.7 Interrupt & Redirect

Pressing Ctrl+C during AI response or tool execution:
1. Stops current operation immediately
2. Preserves conversation history (partial work, tool results so far)
3. Returns to input prompt
4. User types correction or new instruction
5. Agent continues with full context

### 2.8 Output UX

- **Spinner for model calls**: Rich Spinner with elapsed time while waiting for LLM.
- **Streaming tokens**: token-by-token via Rich Live display.
- **Tool progress**: `[1/3] OCR: report_v1.pdf...` with step counter for multi-step operations.
- **Thinking display**: dim/italic text, indented.
- **Final summary**: `Done: 3 files processed, 1 file written (2.3s)`.

### 2.9 Structured Error Messages

Every error has three parts: **what** happened, **why** (if known), and **what to try**:

```
Error: Could not connect to Zhipu API
  Reason: Connection timed out after 30s
  Try:
    1. Check your internet connection
    2. Verify API status at status.bigmodel.cn
    3. Run `zhi config show` to confirm your API key
```

Rendered via Rich Panel (red border for errors, yellow for warnings). Raw stack traces go to `~/.zhi/logs/`, never shown to user unless `--debug`.

### 2.10 File Safety

- **Output directory**: all file writes go to `./zhi-output/` by default (configurable).
- **No overwrite**: refuses to overwrite existing files without confirmation.
- **Path validation**: reject `..` traversal, validate output path is within allowed directory.
- **Rich output formats**: file_write auto-detects from extension (.xlsx, .docx, .md, .json, .csv).
- **Skills restrict tools**: a skill can only use tools listed in its YAML.
- **No delete tool**: the agent cannot delete files at all.
- **Tool output size limits**: cap tool output at 50KB. Truncate with `[truncated, showing first 50KB of 2MB]`.

### 2.11 Non-Interactive Mode

```bash
# One-shot mode
zhi -c "translate this text to Chinese"

# Pipe mode (auto-detected via isatty)
cat report.txt | zhi -c "summarize this"

# Direct CLI skill execution
zhi run translate README.md --to chinese > README_zh.md

# Pipe mode: no color, no spinner, plain output
# Exit code: 0 on success, 1 on error
```

### 2.12 No-Color & Verbose Modes

- `NO_COLOR` env var and `--no-color` flag: no ANSI codes, no emoji, plain text prefixes.
- `-v` verbose: full API request/response payloads, tool details, timing.
- `-vv` double verbose: raw HTTP headers, token counts, cost estimates.
- `/verbose` toggle in REPL.

### 2.13 File Safety Guarantees

`zhi` makes the following guarantees about the user's filesystem:

1. **No deletions**: `zhi` will never delete any file on the user's machine. There is no delete tool. The only deletion capability is `/skill delete`, which removes skill YAML files from zhi's own data directory.
2. **No modifications**: `zhi` will never modify existing files. `file_write` only creates new files. Overwriting an existing file in `zhi-output/` always requires explicit confirmation, even in auto mode.
3. **Scoped output**: All file writes go to `./zhi-output/` (configurable). Path traversal (`..`) is rejected. Symlinks are resolved before writing — if the resolved path is outside the output directory, the write is refused.
4. **Read-only tools**: `file_read`, `file_list`, and `ocr` are read-only. They cannot modify, delete, or create files.
5. **Shell always confirms**: The shell tool always requires explicit user confirmation for every command, regardless of permission mode. Auto mode does NOT apply to shell. A destructive command detector warns about commands containing `rm`, `del`, `mv`, `chmod`, `mkfs`, `dd`, `sed -i`, `>` (redirect), or similar patterns.
6. **Skill name validation**: Skill names must match `^[a-zA-Z0-9][a-zA-Z0-9_-]*$` (max 64 chars). Names containing `/`, `\`, `..`, or other path separators are rejected to prevent path traversal attacks.

### 2.14 Multimodal File Input (Drag-and-Drop)

Users can drag files from their file manager into the terminal. Modern terminals (iTerm2, Windows Terminal, macOS Terminal) convert this to a pasted file path. `prompt_toolkit` receives it as text input.

**Supported file types and routing:**

| File Type | Extensions | Processing |
|-----------|-----------|------------|
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` | Upload to GLM vision API for multimodal chat, or OCR for text extraction |
| PDFs | `.pdf` | OCR via `/v4/layout_parsing` |
| Office docs | `.xlsx`, `.docx` | OCR for text extraction (native parsing deferred to post-v1) |
| Text files | `.txt`, `.md`, `.csv`, `.json`, `.yaml` | Direct `file_read` |

**Auto-detection**: When a file path is detected in user input (absolute path or recognized extension), zhi auto-detects the type and routes to the appropriate tool:

```
You: /Users/name/Desktop/invoice.pdf
  Detected: invoice.pdf (PDF, 2.3MB)
  Processing with OCR...
```

**Input file size limits:**

| Type | Max Size | Behavior on Exceed |
|------|----------|--------------------|
| Images (vision) | 10MB | Auto-resize to 2048px max dimension |
| PDFs (OCR) | 20MB | Reject with suggestion to split |
| Text files | 100KB | Truncate with warning |

**Multiple files**: Users can drag multiple files. Each path appears on a separate line. The agent processes them in sequence.

### 2.15 Internationalization (i18n)

Design principle: Chinese-first internationalization.

**v1 scope (minimal):**
- All user-facing strings (error messages, prompts, help text) are defined as constants in a central `messages.py` module — not hardcoded in logic.
- Default language: English. Chinese translations tracked but deferred to v1.1.
- CJK text rendering (wide characters, IME input) is first-class via `prompt_toolkit`.
- Rich output handles CJK column widths correctly.

**v1.1 scope:**
- `ZHI_LANG` env var or `config.yaml` `language` field to switch locale.
- Message catalog with English and Simplified Chinese.
- Skill YAML `description` field supports multi-language via optional `description_zh` field.

---

## 3. Architecture

```
~/Projects/zhi/
+-- pyproject.toml
+-- README.md
+-- LICENSE (MIT)
+-- src/
|   +-- zhi/
|       +-- __init__.py
|       +-- __main__.py          # python -m zhi
|       +-- cli.py               # Entry point: launches REPL or one-shot
|       +-- repl.py              # Interactive REPL loop + slash command handling
|       +-- config.py            # ~/.zhi/config.yaml + env var fallback + validation
|       +-- client.py            # Zhipu API: chat completions + OCR endpoint + retry
|       +-- agent.py             # Agent loop (tool-calling cycle) + Context
|       +-- ui.py                # Rich: streaming, permission prompts, spinners, errors
|       +-- models.py            # Model registry + metadata
|       +-- errors.py            # Error catalog (structured error messages)
|       +-- tools/
|       |   +-- __init__.py      # Tool registry
|       |   +-- base.py          # BaseTool ABC (name, description, params, execute)
|       |   +-- file_read.py     # Read file contents (safe)
|       |   +-- file_write.py    # Write new files to zhi-output/ (risky)
|       |   +-- file_list.py     # List directory contents (safe)
|       |   +-- ocr.py           # GLM-OCR via /v4/layout_parsing (safe)
|       |   +-- shell.py         # Cross-platform subprocess (risky)
|       |   +-- web_fetch.py     # Fetch URL content (safe)
|       |   +-- skill_create.py  # Create skill YAML files (risky)
|       +-- skills/
|           +-- __init__.py      # Discover skills from builtin + user dir
|           +-- loader.py        # Parse YAML -> SkillConfig with validation
|           +-- builtin/
|               +-- summarize.yaml
|               +-- translate.yaml
+-- tests/
    +-- conftest.py              # Shared fixtures
    +-- unit/
    +-- integration/
    +-- e2e/
    +-- fixtures/
```

**New files vs original plan**: `models.py` (model registry), `errors.py` (error catalog).

---

## 4. Key Design Decisions

### 4.1 Two-Model Architecture
- **Interactive mode** (`zhi`): GLM-5 (smart, expensive). For creating skills, complex reasoning.
- **Skill execution** (`zhi run <skill>`): model from skill YAML, defaults to GLM-4-flash (cheap, fast).
- Override: `zhi run compare-docs --model glm-5`.

### 4.2 Skill YAML Format

```yaml
name: compare-docs
description: Compare two documents and produce a diff report
model: glm-4-flash       # cheap model for daily execution
input:
  description: Two file paths (PDF, image, or text)
  args:
    - name: file1
      type: file
      required: true
    - name: file2
      type: file
      required: true
output:
  description: Markdown comparison report
  directory: zhi-output   # default output location
system_prompt: |
  You are a document comparison assistant.
  ...
tools:
  - file_read
  - file_write
  - ocr
max_turns: 15
```

### 4.3 Agent Loop

```python
def run(context: Context) -> str:
    for _ in range(context.max_turns):
        response = context.client.chat(
            model=context.model,
            messages=context.conversation,
            tools=context.tool_schemas,
        )
        msg = response.choices[0].message
        context.session_tokens += response.usage.total_tokens

        if msg.content:
            context.ui.stream(msg.content)

        if not msg.tool_calls:
            return msg.content

        context.conversation.append(msg)
        for call in msg.tool_calls:
            tool = context.tools[call.function.name]
            if tool.risky and not context.on_permission(tool, call):
                context.conversation.append(denied(call.id))
                continue
            context.ui.show_tool_start(tool, call)
            result = tool.execute(**parse(call.function.arguments))
            context.ui.show_tool_end(tool, result)
            context.conversation.append(tool_result(call.id, result))
```

### 4.4 Permission System

Two modes, ~10 lines of logic:
- **Approve**: `input("Allow? [y/n]: ")` for risky tools.
- **Auto**: execute everything, print what's happening.
- Tools declare `risky = True/False`.

### 4.5 file_write Data Format Contract

The model and file_write tool need a clear contract for structured formats:

| Extension | Expected data shape |
|-----------|-------------------|
| `.xlsx` | `{"sheets": [{"name": "Sheet1", "headers": [...], "rows": [[...]]}]}` |
| `.docx` | `{"content": "markdown string"}` |
| `.csv` | `{"headers": [...], "rows": [[...]]}` |
| `.json` | Pass-through (any valid JSON) |
| `.md`, `.txt` | Plain text string |

Documented in the tool's JSON Schema `description` so the model knows the contract.

### 4.6 Cross-Platform

- `pathlib.Path` everywhere.
- `platformdirs` for config dir (`~/.zhi/` on macOS, `%APPDATA%/zhi` on Windows).
- Shell tool: `subprocess.run(cmd, shell=True)` -- OS-native shell.
- No Unix-only APIs.

### 4.7 Model Registry

```python
MODELS = {
    "glm-5":       {"tier": "premium",  "supports_thinking": True,  "supports_tools": True},
    "glm-4-flash": {"tier": "economy",  "supports_thinking": False, "supports_tools": True},
    "glm-4-air":   {"tier": "economy",  "supports_thinking": False, "supports_tools": True},
}
```

Validate `/model` commands against this. Warn if user picks a model without tool support.

### 4.8 Dependencies

- `zhipuai` -- Zhipu API SDK
- `pyyaml` -- Skill parsing
- `rich` -- Terminal UI (streaming, panels, prompts)
- `prompt_toolkit` -- REPL input with history/autocomplete
- `platformdirs` -- Cross-platform dirs
- `openpyxl` -- Excel output
- `python-docx` -- Word output
- `httpx` -- HTTP requests for web_fetch

**Lazy import strategy**: `openpyxl` and `python-docx` are only imported when `file_write` is called for `.xlsx` or `.docx` formats. This reduces idle memory from ~65MB to ~50MB. These packages are listed as optional extras in `pyproject.toml`:

```toml
[project.optional-dependencies]
excel = ["openpyxl>=3.1"]
word = ["python-docx>=1.0"]
all = ["openpyxl>=3.1", "python-docx>=1.0"]
```

Dev dependencies: `pytest`, `pytest-cov`, `pytest-mock`, `pytest-asyncio`, `ruff`, `mypy`

### 4.9 Config Directory Convention

This document uses `~/.zhi/` as shorthand for the platform-specific config directory resolved by `platformdirs.user_config_dir("zhi")`:

| Platform | Actual Path |
|----------|-------------|
| macOS | `~/Library/Application Support/zhi/` |
| Windows | `%APPDATA%\zhi\` (typically `C:\Users\<name>\AppData\Roaming\zhi\`) |
| Linux | `~/.config/zhi/` (or `$XDG_CONFIG_HOME/zhi/`) |

All references to `~/.zhi/` in this document refer to the platform-appropriate path above. Implementation must use `platformdirs.user_config_dir("zhi")`, never hardcode `~/.zhi/`.

---

## 5. Architecture Improvements

These improvements refine the original plan's architecture based on the audit.

### ARCH-1: Context Dataclass

Replace individual function parameters with a request-scoped `Context` object:

```python
@dataclass
class Context:
    config: ZhiConfig
    client: Client
    model: str
    tools: dict[str, BaseTool]
    tool_schemas: list[dict]
    permission_mode: PermissionMode
    conversation: list[dict]
    ui: UI
    session_tokens: int = 0
    max_turns: int = 30
```

Pass `Context` to the agent loop and REPL. Makes it easy to add features (token tracking, logging) without changing function signatures.

**Stage**: 2 (build into agent.py from the start)

### ARCH-2: Streaming vs Non-Streaming Client

Design the client with both paths from the start:

```python
def chat(self, ...) -> ChatResponse:
    """Non-streaming. Returns complete response."""

def chat_stream(self, ...) -> Iterator[ChatChunk]:
    """Streaming. Yields chunks for live display."""
```

Interactive mode uses `chat_stream`. Skill execution uses `chat`.

**Stage**: 1 (part of client.py)

### ARCH-3: Config Validation

Validate config at load time with a typed dataclass:

```python
@dataclass
class ZhiConfig:
    api_key: str
    default_model: str = "glm-5"
    output_dir: str = "zhi-output"
    max_turns: int = 30
    log_level: str = "INFO"

    def validate(self):
        if not self.api_key:
            raise ConfigError("API key required")
        if self.default_model not in KNOWN_MODELS:
            warn(f"Unknown model: {self.default_model}")
```

**Stage**: 1 (part of config.py)

### ARCH-4: API Retry with Exponential Backoff

```python
def _call_with_retry(self, fn, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except (RateLimitError, ServerError, ConnectionError) as e:
            if attempt == max_retries:
                raise
            wait = min(2 ** attempt + random.uniform(0, 1), 30)
            ui.show_retry(attempt + 1, max_retries, wait)
            time.sleep(wait)
```

Retry on: 429, 500, 503, network timeouts. Fail fast on: 401, 403, 400.

**Stage**: 1 (built into client.py)

### ARCH-5: Structured Error Catalog

Error dataclass:

```python
@dataclass
class ZhiError:
    code: str
    message: str
    suggestions: list[str]
    log_details: str | None = None
```

All user-facing errors rendered via Rich Panel. Stack traces go to `~/.zhi/logs/` only.

**Stage**: 2 (errors.py)

### ARCH-6: Message Role Enum

```python
class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
```

Prevents typos and improves code navigation.

**Stage**: 2 (agent.py)

### ARCH-7: Logging Infrastructure

Structured logging to `~/.zhi/logs/`. Default: INFO to file, WARNING to console. Debug mode via `--debug` or `ZHI_DEBUG=1`.

Log rotation via `logging.handlers.RotatingFileHandler`:
- Max file size: 5MB per log file
- Keep last 3 rotated files (`zhi.log`, `zhi.log.1`, `zhi.log.2`, `zhi.log.3`)
- Total max log footprint: 15MB
- Prevents unbounded disk growth for power users

**Stage**: 2 (integrated into all modules)

---

## 6. Implementation Stages (34 Tasks)

### Dependency Graph

```
Stage 1 (foundation)
  1.1 --> 1.2 --> 1.3
                  1.4 --> 1.5
           1.6
           1.7 (after 1.2-1.6)

Stage 2 (core experience) -- depends on Stage 1
  2.1 --> 2.2
  2.3 --> 2.4
  2.3 --> 2.5, 2.6 --> 2.7, 2.8
  1.4 + 2.1-2.4 --> 2.9 --> 2.10

Stage 3 (extended tools) -- depends on Stage 2
  2.3 --> 3.1, 3.2, 3.3 (parallel)
  3.1 + 2.7 --> 3.4

Stage 4 (skills) -- depends on Stage 2 (can parallel with Stage 3)
  4.1 --> 4.2 --> 4.3, 4.4, 4.5
  4.1 --> 4.6 --> 4.7

Stage 5 (polish) -- depends on Stages 1-4
  All --> 5.1, 5.2, 5.3, 5.4
```

**Critical path**: 1.1 -> 1.2 -> 1.4 -> 2.3 -> 2.4 -> 2.9 -> 2.10 -> 4.4 -> 5.1

**Parallelism**: Stage 3 tools (3.1, 3.2, 3.3) build in parallel. Stage 3 and Stage 4 proceed concurrently. UI work (2.1, 2.2) parallels tool work (2.3-2.8).

---

### Stage 1: Scaffold + Config + Client (7 tasks)

#### Task 1.1: Create Project Scaffold
**Goal**: Installable Python package with entry point.
**Files**: `pyproject.toml`, `src/zhi/__init__.py`, `__main__.py`, `LICENSE`, `.gitignore`
**Details**:
- `[project.scripts]` for `zhi` entry point
- Pin minimum dependency versions
- Include `[project.optional-dependencies] dev = [...]` for test deps
- `__init__.py` exports `__version__` via `importlib.metadata`
- Add `py.typed` marker
**Dependencies**: None
**Tests required before done**: N/A (scaffold only)
**Definition of Done**: `pip install -e .` succeeds; `zhi --version` prints version; `python -m zhi` works.

#### Task 1.2: Implement Config Load/Save
**Goal**: Config system with YAML file, env var fallback, and validation.
**Files**: `config.py`
**Details**:
- Load from `~/.zhi/config.yaml` via `platformdirs`
- `ZHI_API_KEY` env var overrides YAML value
- Schema validation via typed dataclass (ARCH-3)
- Handle corrupt YAML gracefully (re-run wizard, back up old file)
- File permissions 600 on config file
**Dependencies**: 1.1
**Tests required before done**:
- `test_load_config_from_yaml`
- `test_load_config_env_var_override`
- `test_load_config_env_var_only`
- `test_load_config_missing_all`
- `test_save_config`
- `test_config_dir_platform`
- `test_config_yaml_parse_error`
- `test_config_partial_yaml`
- `test_config_permissions_error`
**Definition of Done**: Config loads from file; env var overrides work; invalid YAML gives clear error; missing config triggers first-run path.
**Coverage target**: 90% line, 85% branch.

#### Task 1.3: Implement First-Run Wizard
**Goal**: 3-step onboarding wizard with API key validation.
**Files**: `config.py` (extend)
**Details**:
- Step 1: API key (masked input, immediate validation via model-list call)
- Step 2: Defaults (model, output dir) with Enter-to-accept
- Step 3: Optional demo skill run
- Invalid key: clear message with common fixes
- Wizard only runs once; re-run with `zhi --setup`
**Dependencies**: 1.2
**Tests required before done**:
- `test_config_wizard_saves`
- `test_wizard_first_run_flow`
- `test_wizard_invalid_key_retry`
**Definition of Done**: First run detects missing config, guides user through 3 steps, validates key, saves config. Subsequent runs skip wizard.

#### Task 1.4: Implement Client -- Chat Completions
**Goal**: Zhipu API wrapper with streaming, retry, and error handling.
**Files**: `client.py`
**Details**:
- `chat()` non-streaming method returning complete response
- `chat_stream()` streaming method yielding chunks (ARCH-2)
- Exponential backoff retry for transient errors (ARCH-4)
- Model selection parameter
- Thinking mode parameter
- Token usage extraction from response
**Dependencies**: 1.2
**Tests required before done**:
- `test_chat_completion_basic`
- `test_chat_completion_with_tools`
- `test_chat_completion_streaming`
- `test_chat_invalid_api_key`
- `test_chat_rate_limit`
- `test_chat_server_error`
- `test_chat_network_timeout`
- `test_chat_model_selection`
- `test_chat_thinking_mode`
**Definition of Done**: Client sends prompts, parses responses, handles streaming, retries transient errors, fails fast on auth errors.
**Coverage target**: 85% line, 80% branch.

#### Task 1.5: Implement Client -- OCR Endpoint
**Goal**: OCR via Zhipu layout parsing API.
**Files**: `client.py` (extend)
**Details**:
- POST file to `/v4/layout_parsing`
- Handle async flow: submit -> get task_id -> poll `/v4/async-result/{id}` every 2s -> return on COMPLETED
- Timeout after 60s
- Support PDF and image files
- **Input file size limit**: Reject files over 20MB with clear error message
- **Streaming upload**: Use `httpx.post(url, content=open(path, 'rb'))` to stream file data instead of reading entire file into memory. Keeps memory constant regardless of file size.
**Dependencies**: 1.4
**Tests required before done**:
- `test_ocr_endpoint`
- `test_ocr_invalid_file`
- `test_ocr_large_file`
**Definition of Done**: OCR accepts PDF/image, polls for result, returns markdown text. Errors handled gracefully.

#### Task 1.6: Implement CLI Entry Point
**Goal**: Entry point that launches REPL, one-shot, or skill run.
**Files**: `cli.py`
**Details**:
- `zhi` (no args) -> REPL
- `zhi -c "message"` -> one-shot mode
- `zhi run <skill> [files]` -> direct skill execution
- `zhi --version` -> version info
- `zhi --setup` -> re-run wizard
- `zhi --debug` -> enable debug logging
- `zhi --no-color` -> disable colors
- Detect `isatty(stdin)` for pipe mode
**Dependencies**: 1.1
**Tests required before done**: CLI arg parsing tests (unit)
**Definition of Done**: All CLI modes parse correctly; unknown flags show help.

#### Task 1.7: Write Tests for Stage 1
**Goal**: Full test coverage for config, client, CLI.
**Files**: `tests/unit/test_config.py`, `tests/unit/test_client.py`, `tests/conftest.py`
**Details**:
- `conftest.py` with shared fixtures: mock API client, temp config directory, sample files
- Mock at SDK boundary (`client.chat.completions.create`), not HTTP level
- API error response fixtures in `tests/fixtures/api_responses/`
**Dependencies**: 1.2-1.6
**Tests required before done**: All Stage 1 tests pass (22 unit + 2 integration + 1 E2E)
**Definition of Done**: `pytest tests/unit/test_config.py tests/unit/test_client.py` all green.

**Stage 1 overall Definition of Done**: `pip install -e .` -> `zhi` launches, prompts for API key, validates, saves config.

**Stage 1 performance targets**:
- Error on bad key within 3 seconds
- Config reload picks up changes without re-running wizard

---

### Stage 2: REPL + Tools + Agent Loop (10 tasks)

#### Task 2.1: Implement UI -- Streaming Output
**Goal**: Rich-based streaming display with thinking block rendering.
**Files**: `ui.py`
**Details**:
- `stream()` for token-by-token display via Rich Live
- `show_thinking()` for dim/italic thinking text
- `show_tool_start()` / `show_tool_end()` for tool progress with step counter
- Spinner with elapsed time during model calls
- Final summary line: `Done: N files processed, N written (Xs)`
- Flicker-free rendering (avoid re-rendering entire output per token)
**Dependencies**: 1.1
**Tests required before done**:
- `test_ui_stream_text`
- `test_ui_thinking_display`
- `test_ui_tool_status`
**Coverage target**: 70% line, 60% branch.

#### Task 2.2: Implement UI -- Permission Prompts & Error Display
**Goal**: Permission prompts, structured error rendering.
**Files**: `ui.py` (extend), `errors.py`
**Details**:
- `ask_permission(tool, args)` using Rich Confirm
- Error catalog (ARCH-5): each error has code, message, suggestions, log_details
- Error rendered via Rich Panel (red border). Warnings in yellow.
- No-color fallback: plain text `[ERROR]`, `[TOOL]`, `[DONE]` prefixes
**Dependencies**: 2.1
**Tests required before done**:
- `test_ui_permission_prompt_yes`
- `test_ui_permission_prompt_no`
**Definition of Done**: Permission prompts work in both approve/auto modes. Errors render with 3 parts (what, why, try).

#### Task 2.3: Implement BaseTool ABC
**Goal**: Abstract base class for tools with JSON Schema generation.
**Files**: `tools/base.py`
**Details**:
- Abstract: `name`, `description`, `parameters` (JSON Schema), `risky` flag, `execute()` method
- Auto-generate OpenAI-compatible function schema from class attributes
- `risky` defaults to `False`
**Dependencies**: 1.1
**Tests required before done**:
- `test_base_tool_schema_generation`
- `test_base_tool_risky_flag`
**Coverage target**: 95% line, 90% branch.

#### Task 2.4: Implement Tool Registry
**Goal**: Registry that discovers, registers, and exports tools.
**Files**: `tools/__init__.py`
**Details**:
- Simple dict registry. Validate no duplicate names.
- `register(tool)`, `get(name)`, `list()`, `filter(names)` methods
- Export as OpenAI-format function list for API calls
- Design to not preclude future plugin architecture (entry points)
**Dependencies**: 2.3
**Tests required before done**:
- `test_tool_registry_register`
- `test_tool_registry_duplicate`
- `test_tool_registry_list`
- `test_tool_registry_filter_by_names`
**Definition of Done**: Tools register by name, export schemas, filter by skill's tool list.

#### Task 2.5: Implement file_read Tool
**Goal**: Read file contents safely.
**Files**: `tools/file_read.py`
**Details**:
- Read text files with encoding detection
- Size limit: 100KB cap (truncate with warning)
- Return error for binary files
- Handle permission denied, file not found
- Working-directory scope (reject absolute paths or `..` traversal by default)
**Dependencies**: 2.3
**Tests required before done**:
- `test_file_read_text`
- `test_file_read_nonexistent`
- `test_file_read_binary`
- `test_file_read_large`
- `test_file_read_permission_denied`
- `test_file_read_encoding`
**Coverage target**: 90% line, 85% branch.

#### Task 2.6: Implement file_write Tool -- Plain Text
**Goal**: Write files to `zhi-output/` with safety checks.
**Files**: `tools/file_write.py`
**Details**:
- Default output to `./zhi-output/`, auto-create if missing
- No-overwrite check (confirm in approve mode)
- Path validation: reject `..` traversal, validate within allowed directory
- `risky = True`
- Handles: `.md`, `.txt`, `.json`, `.csv`
- **Symlink resolution**: Before writing, resolve the target path with `Path.resolve()`. If the resolved path is outside the allowed output directory, refuse the write with a clear error. This prevents symlink attacks.
- **Overwrite protection in auto mode**: `file_write` always confirms before overwriting an existing file, even in auto mode. Auto mode does NOT bypass overwrite protection. This is a file safety guarantee.
**Dependencies**: 2.3
**Tests required before done**:
- `test_file_write_text`
- `test_file_write_markdown`
- `test_file_write_json`
- `test_file_write_csv`
- `test_file_write_output_dir`
- `test_file_write_creates_dir`
- `test_file_write_no_overwrite`
- `test_file_write_risky_flag`
- `test_file_write_path_traversal`
- `test_file_write_disk_full`
- `test_file_write_symlink_attack_blocked`
- `test_file_write_auto_mode_overwrite_confirms`
**Coverage target**: 90% line, 85% branch.

#### Task 2.7: Implement file_write Tool -- Rich Formats
**Goal**: Excel and Word output from structured data.
**Files**: `tools/file_write.py` (extend)
**Details**:
- `.xlsx` via `openpyxl`: expects `{"sheets": [{"name": "...", "headers": [...], "rows": [[...]]}]}`
- `.docx` via `python-docx`: expects `{"content": "markdown string"}`
- Format contract documented in tool's JSON Schema description
- Graceful degradation: if openpyxl not installed, fall back to CSV with warning
- If python-docx not installed, fall back to Markdown with warning
**Dependencies**: 2.6
**Tests required before done**:
- `test_file_write_xlsx`
- `test_file_write_docx`
- `test_file_write_permission_denied_write`
**Definition of Done**: Model sends structured data, file_write produces correct format. 1000-row Excel in < 2s.

#### Task 2.8: Implement file_list Tool
**Goal**: List directory contents with metadata.
**Files**: `tools/file_list.py`
**Details**:
- Use `pathlib`. Show filename, size, modified date.
- Cap depth to prevent recursive explosion.
- `risky = False`
**Dependencies**: 2.3
**Tests required before done**:
- `test_file_list_directory`
- `test_file_list_empty`
- `test_file_list_nonexistent`
- `test_file_list_nested`
**Coverage target**: 90% line, 85% branch.

#### Task 2.9: Implement Agent Loop
**Goal**: Core agent loop with tool calling, streaming, and permissions.
**Files**: `agent.py`, `models.py`
**Details**:
- Context dataclass (ARCH-1) for request-scoped state
- Role enum (ARCH-6)
- Tool-calling cycle with message accumulation
- Max_turns guard
- Handle multi-tool calls in single response
- Handle unknown tool names (error back to model)
- Handle tool execution errors (error back to model)
- Permission check (approve/auto modes)
- Ctrl+C handling: cancel API call, preserve messages to interruption point, return to prompt cleanly
- Token tracking from API response usage field
- Streaming output via ui.stream()
**Dependencies**: 1.4, 2.1-2.4
**Tests required before done**:
- `test_agent_single_turn_text`
- `test_agent_single_tool_call`
- `test_agent_multi_tool_calls`
- `test_agent_multi_turn_loop`
- `test_agent_max_turns_limit`
- `test_agent_permission_approve`
- `test_agent_permission_deny`
- `test_agent_safe_tool_no_prompt`
- `test_agent_unknown_tool`
- `test_agent_tool_execution_error`
- `test_agent_empty_response`
- `test_agent_message_history`
- `test_agent_auto_mode`
- `test_agent_interrupt_mid_loop`
**Coverage target**: 90% line, 85% branch.

#### Task 2.10: Implement REPL Loop
**Goal**: Interactive REPL with slash commands, history, and tab completion.
**Files**: `repl.py`
**Details**:
- `prompt_toolkit` input with persistent history (`~/.zhi/history.txt`, max 10K entries)
- History excludes sensitive lines (api_key, password, token, secret)
- Tab completion: slash commands, skill names, model names, file paths
- Multi-line input (backslash continuation)
- Slash command dispatch: `/help`, `/auto`, `/approve`, `/model`, `/think`, `/fast`, `/exit`, `/run`, `/skill`, `/reset`, `/undo`, `/usage`
- Unknown commands show helpful error
- Empty input ignored
- Conversation state management
- Ctrl+C: stop current operation, preserve history, return to prompt
- Ctrl+D (EOF): exit gracefully
- Mode indicator in prompt
- CJK/IME input support
**Dependencies**: 2.9, 2.1
**Tests required before done**:
- `test_repl_help_command`
- `test_repl_exit_command`
- `test_repl_auto_mode`
- `test_repl_approve_mode`
- `test_repl_model_switch`
- `test_repl_model_invalid`
- `test_repl_think_command`
- `test_repl_fast_command`
- `test_repl_unknown_command`
- `test_repl_regular_text`
- `test_repl_run_command`
- `test_repl_skill_list`
- `test_repl_skill_new`
- `test_repl_keyboard_interrupt`
- `test_repl_empty_input`
- Edge cases: `test_edge_eof_input`, `test_edge_slash_only`, `test_edge_slash_with_spaces`
**Coverage target**: 80% line, 75% branch.

**Stage 2 overall Definition of Done**:
- `zhi` -> type messages, get streaming AI responses, use /auto, /approve, write files in xlsx/docx/csv/json/md/txt
- All slash commands work
- Ctrl+C interrupts cleanly
- Tab completion works for commands, models, file paths
- All Stage 2 tests pass (62 unit + 11 integration + 6 E2E)

**Stage 2 performance targets**:
- REPL startup: < 500ms cold, < 300ms warm
- Local tool execution (file_read/write/list): < 100ms for files under 10MB
- Streaming first-token time: < 800ms on stable connection
- file_write xlsx (1000 rows): < 2s
- Memory: < 50MB idle, < 200MB peak (20-turn conversation)

---

### Stage 3: OCR + Shell + Web Tools (5 tasks)

#### Task 3.1: Implement OCR Tool
**Goal**: OCR tool that calls Zhipu layout parsing API.
**Files**: `tools/ocr.py`
**Details**:
- POST file to `/v4/layout_parsing` via client's OCR method
- Handle PDF multi-page and images
- Poll for async results with progress indicator ("OCR processing... (elapsed: Xs)")
- Reject unsupported formats
- Cap output size
- **Input file size limit**: Reject files over 20MB: "File too large for OCR ({size}MB). Maximum: 20MB."
- **Streaming upload**: Stream file to API via httpx instead of buffering in memory.
**Dependencies**: 2.3, 1.5
**Tests required before done**:
- `test_ocr_pdf`
- `test_ocr_image`
- `test_ocr_unsupported_format`
- `test_ocr_api_failure`
- `test_ocr_empty_result`
**Coverage target**: 85% line, 80% branch.

#### Task 3.2: Implement Shell Tool
**Goal**: Cross-platform subprocess with timeout and output limits.
**Files**: `tools/shell.py`
**Details**:
- `subprocess.run(cmd, shell=True, timeout=30)` -- OS-native shell
- `/bin/sh` on macOS/Linux, `cmd.exe` on Windows
- Capture stdout + stderr
- Output limit: truncate at 100KB with warning
- `risky = True`
- **Always requires confirmation**: Override auto mode for shell — every command requires explicit `y/n` regardless of permission mode. This is a non-negotiable file safety guarantee.
- **Process group kill**: Use `subprocess.Popen` with `start_new_session=True` (Unix) or `CREATE_NEW_PROCESS_GROUP` (Windows). On timeout, kill the entire process group via `os.killpg()` to prevent orphan child processes.
- **Destructive command detector**: Before prompting, check command against patterns: `rm`, `del`, `rmdir`, `mv`, `chmod`, `chown`, `mkfs`, `dd`, `shred`, `truncate`, `sed -i`, `git reset --hard`, `git clean`. If matched, show extra-prominent warning: "This command may modify or delete files. Are you sure?"
- **Command blocklist**: Reject obviously catastrophic patterns outright: `rm -rf /`, `rm -rf ~`, `mkfs /dev/`, `:(){ :|:& };:` (fork bomb), `dd if=/dev/zero of=/dev/`. Return error to model.
**Dependencies**: 2.3
**Tests required before done**:
- `test_shell_simple_command`
- `test_shell_exit_code`
- `test_shell_timeout`
- `test_shell_risky_flag`
- `test_shell_cross_platform`
- `test_shell_output_limit`
- `test_shell_always_requires_confirmation`
- `test_shell_process_group_kill`
- `test_shell_destructive_command_warning`
- `test_shell_command_blocklist`
**Coverage target**: 85% line, 80% branch.

#### Task 3.3: Implement Web Fetch Tool
**Goal**: HTTP GET with text extraction and size limits.
**Files**: `tools/web_fetch.py`
**Details**:
- `httpx` GET with timeout (30s default)
- HTML-to-text extraction (basic or via `beautifulsoup4`)
- Cap response at 50KB
- Handle redirects, non-200 status
- Validate URL format
**Dependencies**: 2.3
**Tests required before done**:
- `test_web_fetch_success`
- `test_web_fetch_404`
- `test_web_fetch_timeout`
- `test_web_fetch_invalid_url`
**Coverage target**: 85% line, 80% branch.

#### Task 3.4: Integration Test -- OCR-to-Excel Pipeline
**Goal**: End-to-end test of the plan's key scenario.
**Files**: `tests/integration/test_agent_tools.py` (extend)
**Details**:
- Mock OCR API to return sample text
- Agent chains: OCR -> process -> file_write xlsx
- Verify output Excel file is valid and contains expected data
- Sample test PDF committed to `tests/fixtures/files/`
**Dependencies**: 3.1, 2.7
**Tests required before done**:
- `test_e2e_ocr_to_excel`
**Definition of Done**: "OCR this invoice and save as Excel" completes without manual intervention in auto mode.

#### Task 3.5: Write Unit Tests for Stage 3 Tools
**Goal**: Full mock-based tests for OCR, shell, web fetch.
**Files**: `tests/unit/tools/test_ocr.py`, `test_shell.py`, `test_web_fetch.py`
**Details**:
- Mock API responses for OCR
- Mock subprocess for shell
- Mock httpx for web
- Test timeout handling, error cases, large output truncation
**Dependencies**: 3.1-3.3
**Tests required before done**: All Stage 3 unit tests pass (15 tests)

**Stage 3 overall Definition of Done**:
- "OCR this invoice and save as Excel" works end-to-end
- Shell runs cross-platform with timeout
- Web fetch handles errors gracefully
- All Stage 3 tests pass (15 unit + 1 integration)

**Stage 3 performance target**: OCR round-trip < 5s for a single-page PDF.

---

### Stage 4: Skill System (8 tasks)

#### Task 4.1: Implement YAML Loader
**Goal**: Parse and validate skill YAML files.
**Files**: `skills/loader.py`
**Details**:
- Load YAML, validate required fields (name, description, system_prompt, tools)
- Validate `tools` list against registered tool names
- Defaults: `model` -> `glm-4-flash`, `max_turns` -> 15
- Ignore unknown fields with warning
- Report clear errors for malformed YAML (include line number)
- Handle empty files, binary files
- CJK skill names work correctly
- **Skill name validation**: Names must match `^[a-zA-Z0-9][a-zA-Z0-9_-]*$` (max 64 chars). Reject names containing `/`, `\`, `..`, spaces, or other path separators. This prevents path traversal via skill names in `skill_create` and `/skill delete`.
**Dependencies**: 1.1
**Tests required before done**:
- `test_load_valid_skill`
- `test_load_minimal_skill`
- `test_load_malformed_yaml`
- `test_load_missing_required_fields`
- `test_load_unknown_tool_reference`
- `test_load_extra_fields_ignored`
- `test_load_empty_file`
- `test_skill_model_default`
- `test_skill_max_turns_default`
- `test_edge_skill_unicode_name`
- `test_skill_name_path_traversal_rejected`
- `test_skill_name_special_chars_rejected`
**Coverage target**: 95% line, 90% branch.

#### Task 4.2: Implement Skill Discovery
**Goal**: Find skills in builtin + user directories.
**Files**: `skills/__init__.py`
**Details**:
- Scan `src/zhi/skills/builtin/` and `~/.zhi/skills/`
- User overrides builtin if same name
- Handle missing user dir (no error)
- Skip corrupted YAML with warning (don't crash)
- Return list with name, description, source (builtin/user), model
**Dependencies**: 4.1
**Tests required before done**:
- `test_discover_builtin_skills`
- `test_discover_user_skills`
- `test_discover_merge`
- `test_discover_empty_user_dir`
- `test_discover_corrupted_skill_skipped`
**Definition of Done**: `/skill list` finds all skills. Corrupted YAML doesn't crash.
**Performance target**: < 200ms with 50 skills installed.

#### Task 4.3: Create Builtin Skills
**Goal**: Two starter skills that work out of the box.
**Files**: `skills/builtin/summarize.yaml`, `skills/builtin/translate.yaml`
**Details**:
- `summarize`: file_read input, text output, GLM-4-flash
- `translate`: text input, text output, GLM-4-flash
- Tested system prompts iterated for quality
- Include sample input text for onboarding demo
**Dependencies**: 4.1
**Tests required before done**: Manual test of both skills. Integration test that loads and validates them.
**Definition of Done**: Both skills load without error, run correctly with GLM-4-flash.

#### Task 4.4: Implement /run Command
**Goal**: Execute a skill with its model and tool restrictions.
**Files**: `repl.py` (extend), `agent.py` (extend)
**Details**:
- Parse `/run <skill> [files]` arguments
- Load skill, validate required args
- Configure agent with skill's model, system_prompt, tool subset
- Thinking OFF by default for skill execution
- Map file args to context in messages
- `--model` flag to override skill's model
- Handle missing skill with helpful error
**Dependencies**: 4.2, 2.9
**Tests required before done**:
- `test_skill_load_and_run`
- `test_skill_tool_restriction`
- `test_skill_model_override`
- `test_skill_args_passed`
- `test_skill_max_turns_enforced`
- `test_skill_thinking_off_by_default`
- `test_edge_run_nonexistent_skill`
**Definition of Done**: `/run summarize file.txt` runs with GLM-4-flash, restricted to skill's tools, produces output.

#### Task 4.5: Implement /skill list, show, edit, delete
**Goal**: Skill management commands.
**Files**: `repl.py` (extend)
**Details**:
- `/skill list`: Rich table with name, description, model, source
- `/skill show <name>`: full YAML with syntax highlighting
- `/skill edit <name>`: open in `$EDITOR` (fallback to inline display)
- `/skill delete <name>`: confirmation prompt, then remove YAML file
**Dependencies**: 4.2
**Tests required before done**:
- `test_repl_skill_list`
**Definition of Done**: All `/skill` subcommands work correctly.

#### Task 4.6: Implement skill_create Tool
**Goal**: AI-assisted skill creation that generates valid YAML.
**Files**: `tools/skill_create.py`
**Details**:
- Tool receives skill data from model (name, description, tools, system_prompt, etc.)
- Validate against registered tools
- Preview YAML to user for confirmation
- Save to `~/.zhi/skills/<name>.yaml`
- Handle duplicate names (ask for overwrite)
- `risky = True`
- **Name sanitization**: Validate skill name before saving. Must match `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`. Reject path separators and traversal patterns.
**Dependencies**: 4.1, 2.3
**Tests required before done**:
- `test_skill_create_valid`
- `test_skill_create_validates_tools`
- `test_skill_create_risky_flag`
- `test_skill_create_duplicate_name`
**Coverage target**: 85% line, 80% branch.

#### Task 4.7: Implement /skill new Command
**Goal**: Enter skill creation mode using GLM-5.
**Files**: `repl.py` (extend)
**Details**:
- Switch to GLM-5 for skill creation conversation
- Offer template selection: blank, file-process, web-extract, translate
- Templates pre-fill tools, system_prompt skeleton, input args
- After skill saved, return to previous model
**Dependencies**: 4.6
**Tests required before done**:
- `test_repl_skill_new`
- `test_e2e_create_and_run_skill`
**Definition of Done**: User starts `/skill new`, gets template options, creates a skill conversationally, skill is immediately runnable.

#### Task 4.8: Write Tests for Skill System
**Goal**: Full test coverage for loader, discovery, commands, creation.
**Files**: `tests/unit/skills/`, `tests/integration/test_skill_execution.py`, `tests/e2e/test_skill_workflow.py`, `tests/fixtures/skills/`
**Details**:
- Fixture YAML files: valid, minimal, malformed, missing fields, extra fields
- Test YAML validation (valid + 7 invalid cases)
- Test skill discovery with real filesystem (tmp_path)
- E2E: create skill -> run skill -> verify output
**Dependencies**: 4.1-4.7
**Tests required before done**: All Stage 4 tests pass (19 unit + 6 integration + 4 E2E)

**Stage 4 overall Definition of Done**:
- Create a skill conversationally, `/run` it, see output file
- Builtin summarize and translate work
- `/skill list`, `/skill show`, `/skill edit`, `/skill delete` all work
- Two-model split verified: interactive uses GLM-5, `/run` uses skill's model
- All Stage 4 tests pass

**Stage 4 performance target**: Skill YAML parse < 50ms; discovery < 200ms with 50 skills.

---

### Stage 5: Polish + Publish (4 tasks)

#### Task 5.1: Error UX Pass
**Goal**: All failure modes produce friendly, actionable error messages.
**Files**: `errors.py` (extend), all modules
**Details**:
- Implement full error message catalog (see Section 2.9)
- Catch zhipuai exceptions, network errors, file not found, etc.
- No stack traces unless `--debug`
- All errors logged to `~/.zhi/logs/`
- Graceful degradation when API unreachable (slash commands still work)
**Dependencies**: All stages
**Tests required before done**: Error edge case tests (7 API failure tests, 7 filesystem tests, 5 REPL edge cases)
**Definition of Done**: Every common failure produces a single-line actionable message with suggestions. `--debug` shows full traces.

#### Task 5.2: Write README
**Goal**: Complete documentation for users and skill authors.
**Files**: `README.md`
**Details**:
- Install (pip, uv)
- Quickstart (< 2 min to first response)
- Skill authoring guide with YAML reference
- Configuration reference
- Model info and cost expectations
- Include GIF/screenshot of REPL session
- Slash command reference
- Troubleshooting section
**Dependencies**: All stages
**Definition of Done**: New user can install and get first response within 2 minutes following README.

#### Task 5.3: GitHub Actions CI
**Goal**: Automated lint, test, and type check pipeline.
**Files**: `.github/workflows/ci.yml`, `.github/workflows/nightly.yml`
**Details**:
- **Every PR** (< 3 min): ruff check, ruff format, mypy --strict, pytest unit (Python 3.10/3.11/3.12), pytest integration
- **Nightly** (< 15 min): cross-platform matrix (macOS + Windows + Linux x Python 3.10/3.11/3.12), E2E tests, pip-audit dependency scan
- Coverage upload to Codecov. Fail under 80%.
**Dependencies**: 1.7
**Tests required before done**: CI pipeline runs green on all platforms.
**Definition of Done**: PRs get automated feedback. Nightly catches cross-platform issues.

#### Task 5.4: PyPI Publish Pipeline
**Goal**: Automated release to PyPI on tag push.
**Files**: `.github/workflows/release.yml`
**Details**:
- Trigger on `v*` tag push
- Run full test suite on macOS + Windows + Linux
- Build sdist + wheel
- Publish via trusted publishers (OIDC) -- test on TestPyPI first
**Dependencies**: 5.3
**Tests required before done**: Test release on TestPyPI succeeds.
**Definition of Done**: `git tag v0.1.0 && git push --tags` -> package on PyPI. Fresh `pip install zhi` works.

**Stage 5 overall Definition of Done**:
- All errors are friendly and actionable
- README enables < 2 min onboarding
- CI runs on every PR; nightly catches cross-platform issues
- `pip install zhi` on a clean virtualenv works on macOS + Windows
- Full workflow (config, chat, OCR, skill create, skill run, skill list) succeeds on fresh install

---

## 7. Gaps & Risks

### Must-Fix Before v1 (blocks usability)

| ID | Gap | Severity | Mitigation | Stage |
|----|-----|----------|-----------|-------|
| GAP-1 | No API error handling / retry strategy | High | Exponential backoff retry (ARCH-4). Max 3 retries. Fail fast on 401/403. | 1 |
| GAP-5 | No graceful degradation when API unreachable | Medium | Slash commands always work (local). AI operations fail with clear message. | 2 |
| GAP-6 | No input validation on file paths from model | High | file_write validates output within `zhi-output/`. file_read scopes to working dir. Reject `..` traversal. | 2 |
| GAP-11 | No max output size for tools | Medium | Cap at 50KB. Truncate with warning. Prevents context window blow-up and cost spikes. | 2 |
| GAP-12 | No file_write data format contract | High | Define explicit JSON Schema contracts per format (see Section 4.5). | 2 |
| COMP-4 | Ctrl+C / signal handling not detailed | High | `signal.signal(SIGINT, handler)` to catch interrupts. Cancel API call, preserve messages, return to prompt cleanly. No stack trace. | 2 |
| GAP-13 | Shell tool can delete/modify user files in auto mode | Critical | Shell always requires confirmation regardless of mode. Destructive command detector. Process group kill on timeout. | 3 |
| GAP-14 | Skill name path traversal in skill_create and /skill delete | High | Validate skill names: `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`. Reject path separators. | 4 |
| GAP-15 | Symlink attack in file_write output directory | Medium | Resolve symlinks with `Path.resolve()`. Verify resolved path is within output dir. | 2 |
| GAP-16 | No log rotation — unbounded disk growth | Medium | `RotatingFileHandler`, 5MB max per file, keep 3 files = 15MB max. | 2 |
| GAP-17 | No OCR input file size limit — memory spike risk | Medium | Reject files over 20MB. Use streaming upload via httpx. | 3 |

### Should-Fix for v1 (significantly improves experience)

| ID | Gap | Severity | Mitigation | Stage |
|----|-----|----------|-----------|-------|
| GAP-2 | No logging infrastructure | Medium | Structured logging to `~/.zhi/logs/`. INFO to file, WARNING to console. Debug mode via `--debug`. | 2 |
| GAP-4 | No token counting or cost awareness | Medium | Track tokens per session from API response. Display at exit. `/usage` command. | 2 |
| GAP-7 | No streaming for tool outputs | Low | Rich spinner/progress during tool execution. OCR: "OCR processing... (elapsed: Xs)". | 2 |
| GAP-8 | OCR async polling not detailed | Medium | Document flow: POST -> task_id -> poll every 2s -> return on COMPLETED. Timeout 60s. | 3 |
| GAP-9 | No `--version` flag | Low | `zhi --version` from `importlib.metadata`. | 1 |
| GAP-10 | Skill YAML injection risk (shell in shared skills) | Medium | Trust prompt on first run of new skill: "This skill uses: shell, file_write. Allow? [y/n]". | 4 |

### Deferred to Post-v1

| ID | Gap | Impact | Notes |
|----|-----|--------|-------|
| GAP-3 | No conversation persistence / session recovery | Medium | Auto-save to `~/.zhi/sessions/`. `/resume` command. |
| COMP-2 | Rate limiting awareness | Low | Track requests/minute, proactively slow down. |
| COMP-3 | Config migration between versions | Low | Sequential migration functions. |
| ARCH-2 (event hooks) | Event-based tool execution hooks | Low | Decouple agent from UI for testability. |
| ARCH-3 (tool results) | Structured ToolResult dataclass | Low | Better UI, artifact tracking, token awareness. |
| ARCH-4 (plugins) | Plugin-ready tool architecture | Low | Entry points for third-party tools. |

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Zhipu API instability (primary audience in China) | Medium | High | Retry logic, graceful degradation, clear error messages |
| GLM-4-flash tool calling quality | Medium | High | Well-crafted skill prompts, max_turns guard, fallback to GLM-5 |
| openpyxl/python-docx add significant install size | Low | Medium | Make optional dependencies with graceful fallback |
| Skill YAML format may need breaking changes | Medium | Medium | Version field in YAML, migration logic in loader |
| CJK text rendering issues on Windows | Medium | Medium | Test explicitly on Windows Terminal, PowerShell, cmd.exe |
| `prompt_toolkit` behavior differences across platforms | Low | Medium | Test on both macOS and Windows CI |

---

## 8. CI/CD & Quality

### 8.1 Test Structure

```
tests/
+-- conftest.py              # Shared fixtures (mock client, tmp dirs, sample skills)
+-- unit/
|   +-- test_config.py
|   +-- test_client.py
|   +-- test_agent.py
|   +-- test_repl.py
|   +-- test_ui.py
|   +-- tools/
|   |   +-- test_base.py
|   |   +-- test_file_read.py
|   |   +-- test_file_write.py
|   |   +-- test_file_list.py
|   |   +-- test_ocr.py
|   |   +-- test_shell.py
|   |   +-- test_web_fetch.py
|   |   +-- test_skill_create.py
|   +-- skills/
|       +-- test_loader.py
|       +-- test_discovery.py
+-- integration/
|   +-- test_agent_tools.py
|   +-- test_skill_execution.py
|   +-- test_repl_agent.py
|   +-- test_config_wizard.py
+-- e2e/
|   +-- test_first_run.py
|   +-- test_interactive_session.py
|   +-- test_skill_workflow.py
+-- fixtures/
    +-- skills/          (valid, minimal, malformed, missing fields, extra fields)
    +-- files/           (sample.txt, sample.pdf, sample.csv)
    +-- api_responses/   (chat_completion.json, tool_calls.json, ocr_response.json, errors/)
```

**Total: ~148 tests** (unit + integration + E2E)

### 8.2 Test Principles

1. **Mock at boundaries, not internals**: Mock Zhipu SDK and filesystem, not internal functions.
2. **Every tool test uses tmp_path**: No test writes to real filesystem.
3. **Fixture-based API responses**: Pre-recorded JSONs in `tests/fixtures/`.
4. **Test names describe behavior**: `test_agent_permission_deny_continues` not `test_agent_3`.
5. **One assertion per test where practical**.
6. **Fast by default**: Unit tests < 10s total. Integration < 30s.
7. **No network calls in tests**: All external APIs mocked.
8. **Cross-platform via parametrize**: monkeypatch to simulate Windows paths on macOS CI and vice versa.

### 8.3 Mock Strategy

| Level | What's mocked | What's real |
|-------|--------------|-------------|
| Unit | SDK client, filesystem (tmp_path), user input | Nothing external |
| Integration | SDK client only | Filesystem (tmp_path), real tool execution |
| E2E | SDK client only | Everything else (tmp_path for isolation) |

### 8.4 Coverage Targets

| Module | Line Coverage | Branch Coverage |
|--------|-------------|----------------|
| `config.py` | 90% | 85% |
| `client.py` | 85% | 80% |
| `agent.py` | 90% | 85% |
| `tools/base.py` | 95% | 90% |
| `tools/file_*.py` | 90% | 85% |
| `tools/ocr.py`, `shell.py`, `web_fetch.py` | 85% | 80% |
| `skills/loader.py` | 95% | 90% |
| **Overall** | **85%** | **80%** |

### 8.5 CI Pipelines

**Every PR** (< 3 minutes):
- `ruff check` + `ruff format --check`
- `mypy --strict`
- `pytest tests/unit/` on Python 3.10, 3.11, 3.12
- `pytest tests/integration/`
- Coverage upload (fail under 80%)

**Nightly** (< 15 minutes):
- Cross-platform matrix: macOS + Windows + Linux x Python 3.10/3.11/3.12
- Full test suite (unit + integration + E2E)
- `pip-audit` dependency security scan

**Release** (on `v*` tag):
- Full test suite on macOS + Windows + Linux
- Build sdist + wheel
- Publish to PyPI via trusted publishers (OIDC)

### 8.6 Linting Configuration

```toml
[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "RUF"]
known-first-party = ["zhi"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: Unit tests (fast, no external deps)",
    "integration: Integration tests (mock API only)",
    "e2e: End-to-end tests (full workflow)",
    "slow: Tests that take >5 seconds",
    "xplat: Cross-platform specific tests",
]

[tool.coverage.run]
source = ["zhi"]
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

---

## 9. Metrics & Telemetry

### 9.1 Performance Targets

| Metric | Target | How to Measure | Stage |
|--------|--------|---------------|-------|
| REPL startup time | < 500ms cold, < 300ms warm | `hyperfine` in CI | 2 |
| Local tool execution (file_read/write/list) | < 100ms (files < 10MB) | Timing decorator on execute() | 2 |
| OCR round-trip | < 5s (single-page PDF) | Instrument API call timing | 3 |
| Streaming first-token | < 800ms (stable connection) | Delta between chat() call and first chunk | 2 |
| Skill YAML parse | < 50ms per skill | Benchmark loader.load() | 4 |
| Skill discovery | < 200ms with 50 skills | Benchmark /skill list | 4 |
| file_write xlsx (1000 rows) | < 2s | Benchmark with synthetic data | 2 |
| Memory (idle REPL) | < 50MB RSS | `psutil.Process().memory_info().rss` | 2 |
| Memory (peak, 20 turns) | < 200MB RSS | Monitor during integration test | 2 |

### 9.2 Reliability Targets

| Scenario | Target | Stage |
|----------|--------|-------|
| API timeout/rate limit/server error | 100% graceful handling (retry + clear error) | 1 |
| Malformed tool call from model | > 90% self-correction (model retries) | 2 |
| Tool execution failure | > 80% model adaptation | 2 |
| Network loss mid-stream | 100% graceful (partial response + error) | 2 |
| Invalid skill YAML | 100% clear error with line number | 4 |
| Ctrl+C during execution | 100% clean interrupt | 2 |

### 9.3 Graceful Degradation Matrix

| Scenario | Degraded Behavior | Stage |
|----------|-------------------|-------|
| No internet | Error on API call; slash commands + skill listing still work | 2 |
| OCR endpoint down | OCR tool errors; other tools still work | 3 |
| openpyxl not installed | file_write falls back to CSV with warning | 2 |
| python-docx not installed | file_write falls back to Markdown with warning | 2 |
| Config file corrupted | Re-run wizard, back up old file | 1 |
| Skill YAML has unknown fields | Ignore with warning, load known fields | 4 |

### 9.4 Cost Tracking

Track token usage from API response `usage` field:

| Feature | Stage |
|---------|-------|
| Per-session token counter (display at `/exit`) | 2 |
| Per-session cost estimate (based on model pricing) | 2 |
| `/usage` command (tokens in/out, cost, model breakdown) | 2 |
| Per-skill-run cost display | 4 |
| Cost comparison when switching models | 4 |

**Cost targets** (per typical session):

| Session Type | Model | Est. Cost |
|-------------|-------|-----------|
| Quick chat (5 turns, no tools) | GLM-5 | ~$0.02-0.05 |
| Complex task (10 turns, 3 tools) | GLM-5 | ~$0.08-0.15 |
| Skill execution (simple) | GLM-4-flash | ~$0.001-0.003 |
| Skill execution (OCR + write) | GLM-4-flash + OCR | ~$0.005-0.01 |
| Skill creation | GLM-5 | ~$0.05-0.10 |

### 9.5 Code Quality Metrics

| Metric | Target | Tool |
|--------|--------|------|
| Type annotation coverage (public API) | > 90% | mypy --strict |
| No `Any` in public APIs | 0 occurrences | mypy + grep |
| Type errors in CI | 0 | mypy in GitHub Actions |
| Overall test coverage | > 85% line, > 80% branch | pytest-cov |

### 9.6 User Adoption Metrics (Optional, Opt-In Telemetry)

Disabled by default. Enabled with `zhi config set telemetry true`. All aggregated, never individual.

| Metric | Target |
|--------|--------|
| First-run success rate | > 90% |
| Time to first response | < 60s (including wizard) |
| Skill creation completion rate | > 70% |
| Median session length | > 5 turns |
| Return rate (3+ days in 2 weeks) | > 40% |
| Error frustration rate (session ends within 30s of error) | < 15% |

---

## 10. Post-v1 Roadmap

### High Impact

| Feature | Effort | Notes |
|---------|--------|-------|
| Skill sharing (export/import/community index) | High | `.zhi-skill` files, security prompts on import |
| Non-interactive mode (`-c`, pipe, `zhi run`) | Medium | Already scoped in v1; expand for automation |
| Conversation save/resume | Medium | Auto-save to `~/.zhi/sessions/`, `/resume` command |

### Medium Impact

| Feature | Effort | Notes |
|---------|--------|-------|
| Skill chaining (pipe syntax) | High | `/run ocr-extract file.pdf \| /run summarize` |
| Project/context awareness | Medium | Auto-detect project type, adjust system prompt |
| Plugin architecture (entry points) | Medium | Third-party tool packages |
| Structured ToolResult | Low | Better UI, artifact tracking |

### Low Impact

| Feature | Effort | Notes |
|---------|--------|-------|
| Skill versioning with history | Medium | Git-style diffs in `~/.zhi/skills/<name>/versions/` |
| Color themes (dark/light auto-detect) | Medium | 2 built-in themes |
| Voice input | High | Chinese voice input via Zhipu or Whisper |
| Event-based tool execution hooks | Low | Decouple agent from UI |
| Config migration | Low | Sequential migration functions |
| Rate limiting awareness | Low | Track requests/minute |

---

## Cross-Platform Parity Checklist

| Feature | macOS | Windows | How Verified |
|---------|-------|---------|-------------|
| `pip install zhi` | Native | Native | CI matrix |
| Config location | `~/.zhi/` | `%APPDATA%/zhi/` | Unit test + platformdirs |
| REPL input + history | prompt_toolkit | prompt_toolkit | Both platforms in nightly CI |
| All slash commands | Same | Same | Platform-agnostic tests |
| file_write all formats | Same | Same | Byte-compare in CI |
| Shell tool | `/bin/sh` | `cmd.exe` | Integration test on both |
| Unicode/CJK output | Works | Works (Windows Terminal) | Manual test |
| Ctrl+C interrupt | SIGINT | SIGINT | Signal handling test |

---

## Test-to-Stage Mapping (Summary)

| Stage | Unit Tests | Integration Tests | E2E Tests | Total |
|-------|-----------|-------------------|-----------|-------|
| Stage 1 | 22 (config, client) | 2 (wizard) | 1 (first run) | 25 |
| Stage 2 | 62 (agent, repl, ui, tools) | 11 (agent+tools, REPL+agent) | 6 (interactive session) | 79 |
| Stage 3 | 15 (ocr, shell, web) | 1 (OCR-to-Excel) | - | 16 |
| Stage 4 | 19 (loader, discovery, create) | 6 (skill execution) | 4 (skill workflow) | 29 |
| Stage 5 | - | - | Full validation | - |
| **Total** | **~118** | **~20** | **~11** | **~148** |
