# zhi CLI — Architecture Audit & Task Breakdown

> **Note**: This document has been synthesized into [05-improved-plan.md](./05-improved-plan.md), which is the authoritative implementation plan. This document is retained as the original architecture audit for reference.

> Based on: `~/docs/plans/2026-02-23-zhi-cli-design.md`
> Analyst: architecture agent
> Date: 2026-02-23

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Stage-by-Stage Task Breakdown](#stage-by-stage-task-breakdown)
3. [Dependency Graph](#dependency-graph)
4. [Gaps, Risks & Missing Pieces](#gaps-risks--missing-pieces)
5. [Architecture Improvements](#architecture-improvements)
6. [Missing Components](#missing-components)

---

## Executive Summary

The plan is well-structured with a clear two-model architecture and pragmatic scope. Below I break each of the 5 stages into granular sub-tasks (~1-2 hours each), identify dependencies, flag risks, and suggest improvements. Total estimated sub-tasks: **34**.

---

## Stage-by-Stage Task Breakdown

### Stage 1: Scaffold + Config + Client (7 sub-tasks)

| ID | Sub-task | Est. | Dependencies | Notes |
|----|----------|------|--------------|-------|
| 1.1 | **Create project scaffold** — `pyproject.toml` with all deps, `src/zhi/__init__.py`, `__main__.py`, `LICENSE`, `.gitignore` | 1h | None | Use `[project.scripts]` for `zhi` entry point. Pin minimum dep versions. |
| 1.2 | **Implement `config.py` — load/save** — `~/.zhi/config.yaml` via platformdirs, env var fallback (`ZHI_API_KEY`), schema with defaults | 1.5h | 1.1 | Validate config schema on load. Handle corrupt YAML gracefully. |
| 1.3 | **Implement first-run wizard** — interactive prompt for API key, optional model preference, save to config | 1h | 1.2 | Use `prompt_toolkit` or plain `input()`. Mask API key input. |
| 1.4 | **Implement `client.py` — chat completions wrapper** — `zhipuai` SDK init, `chat()` method with model/messages/tools params, streaming support | 1.5h | 1.2 | Handle API key validation (test call on first setup). Return typed response objects. |
| 1.5 | **Implement `client.py` — OCR endpoint** — POST to `/v4/layout_parsing`, handle async polling if needed, return markdown text | 1.5h | 1.4 | OCR is async (returns task ID). Need polling logic. |
| 1.6 | **Implement `cli.py` — entry point** — arg parsing (bare `zhi` vs `zhi run <skill>`), launch REPL or one-shot | 1h | 1.1 | Use `argparse` or `click`. Keep minimal — REPL does the heavy lifting. |
| 1.7 | **Write tests for Stage 1** — config load/save, env var fallback, client mock, CLI entry point | 1.5h | 1.2-1.6 | Mock API calls. Test config file creation, missing key errors. |

**Stage 1 verification**: `pip install -e .` -> `zhi` launches, prompts for API key, saves config.

---

### Stage 2: REPL + Tools + Agent Loop (10 sub-tasks)

| ID | Sub-task | Est. | Dependencies | Notes |
|----|----------|------|--------------|-------|
| 2.1 | **Implement `ui.py` — streaming output** — Rich console, `stream()` for token-by-token display, thinking block rendering (dimmed) | 1.5h | 1.1 | Use `rich.live` or manual `console.print`. Handle thinking vs content segments. |
| 2.2 | **Implement `ui.py` — permission prompts & spinners** — `ask_permission(tool, args)`, loading spinners during API calls | 1h | 2.1 | Simple `Confirm.ask()` from Rich. |
| 2.3 | **Implement `tools/base.py` — BaseTool ABC** — abstract `name`, `description`, `parameters` (JSON Schema), `risky` flag, `execute()` method | 1h | 1.1 | Auto-generate JSON schema from type hints or manual dict. |
| 2.4 | **Implement `tools/__init__.py` — tool registry** — discover tools, register by name, lookup, export as OpenAI-format function list | 1h | 2.3 | Simple dict registry. Validate no duplicate names. |
| 2.5 | **Implement `tools/file_read.py`** — read text files, handle encoding detection, size limits | 1h | 2.3 | Cap at ~100KB to avoid blowing context. Return error for binary files. |
| 2.6 | **Implement `tools/file_write.py` — plain text** — write to `zhi-output/`, no-overwrite check, create output dir | 1h | 2.3 | Resolve relative paths. Confirm before overwrite in approve mode. |
| 2.7 | **Implement `tools/file_write.py` — rich formats** — `.xlsx` (openpyxl), `.docx` (python-docx), `.csv`, `.json` format detection & conversion | 2h | 2.6 | Model sends structured data (list of dicts for xlsx, etc.). Need clear data format contract. |
| 2.8 | **Implement `tools/file_list.py`** — list directory contents with metadata (size, modified date) | 0.5h | 2.3 | Use `pathlib`. Cap depth to prevent recursive explosion. |
| 2.9 | **Implement `agent.py` — agent loop** — tool-calling cycle, message accumulation, max_turns guard, streaming | 2h | 1.4, 2.1-2.4 | Core loop from the plan. Handle multi-tool calls in single response. |
| 2.10 | **Implement `repl.py` — REPL loop** — `prompt_toolkit` input with history, slash command dispatch, conversation state, Ctrl+C handling | 2h | 2.9, 2.1 | History persistence to `~/.zhi/history`. Autocomplete for slash commands. |

**Stage 2 verification**: `zhi` -> type messages, get AI responses, use /auto, /approve, write files in multiple formats.

---

### Stage 3: OCR + Shell + Web Tools (5 sub-tasks)

| ID | Sub-task | Est. | Dependencies | Notes |
|----|----------|------|--------------|-------|
| 3.1 | **Implement `tools/ocr.py`** — POST to `/v4/layout_parsing`, handle file upload, poll for results, return extracted markdown | 1.5h | 2.3, 1.5 | Reuse client's OCR method. Handle PDF multi-page. Support images too. |
| 3.2 | **Implement `tools/shell.py`** — cross-platform subprocess with timeout, output capture, error handling | 1.5h | 2.3 | `subprocess.run(cmd, shell=True, timeout=30)`. Sanitize? Or trust model + permission system. |
| 3.3 | **Implement `tools/web_fetch.py`** — HTTP GET, HTML-to-text extraction, size limits | 1.5h | 2.3 | Use `httpx`. Strip HTML with basic approach (or `beautifulsoup4`). Cap response length. |
| 3.4 | **Integration test: OCR-to-Excel pipeline** — end-to-end test: OCR a PDF, process with agent, write Excel | 1.5h | 3.1, 2.7 | The plan's key scenario. May need sample test PDFs. |
| 3.5 | **Write unit tests for Stage 3 tools** — mock API responses for OCR, subprocess for shell, httpx for web | 1h | 3.1-3.3 | Test timeout handling, error cases, large output truncation. |

**Stage 3 verification**: "OCR this invoice and save as Excel" works end-to-end.

---

### Stage 4: Skill System (8 sub-tasks)

| ID | Sub-task | Est. | Dependencies | Notes |
|----|----------|------|--------------|-------|
| 4.1 | **Implement `skills/loader.py` — YAML parsing** — load skill YAML, validate schema (required fields, known tool names), return typed SkillConfig | 1.5h | 1.1 | Validate `tools` list against registered tools. Report clear errors for malformed YAML. |
| 4.2 | **Implement `skills/__init__.py` — skill discovery** — scan builtin dir + `~/.zhi/skills/`, merge, deduplicate (user overrides builtin) | 1h | 4.1 | Watch for name collisions. List with metadata. |
| 4.3 | **Create builtin skills** — `summarize.yaml` and `translate.yaml` with tested system prompts | 1h | 4.1 | Test these manually. Iterate on system prompts for quality. |
| 4.4 | **Implement `/run <skill>` command** — parse args, load skill, configure agent with skill's model/prompt/tools, execute | 1.5h | 4.2, 2.9 | Map skill input args to files. Validate required args. |
| 4.5 | **Implement `/skill list` command** — display available skills with name + description in a Rich table | 0.5h | 4.2 | Show source (builtin vs user). |
| 4.6 | **Implement `tools/skill_create.py`** — AI-assisted skill creation, generate YAML from conversation, save to `~/.zhi/skills/` | 2h | 4.1, 2.3 | The model generates the YAML. Validate before saving. Preview to user for confirmation. |
| 4.7 | **Implement `/skill new` command** — enter skill creation mode, use GLM-5 + skill_create tool | 1h | 4.6 | Switch to GLM-5 for this interaction. Return to previous model after. |
| 4.8 | **Write tests for skill system** — loader validation, discovery, run command, skill creation | 1.5h | 4.1-4.7 | Test malformed YAML, missing tools, skill override logic. |

**Stage 4 verification**: Create a skill conversationally, `/run` it, see output file.

---

### Stage 5: Polish + Publish (4 sub-tasks)

| ID | Sub-task | Est. | Dependencies | Notes |
|----|----------|------|--------------|-------|
| 5.1 | **Error UX pass** — friendly error messages for all failure modes (API down, invalid key, missing files, tool errors), colored output | 1.5h | All | Catch `zhipuai` exceptions, network errors, file not found, etc. |
| 5.2 | **Write README** — install, quickstart, skill authoring guide, model info, cost expectations | 1.5h | All | Include GIF/screenshot of REPL session. |
| 5.3 | **GitHub Actions CI** — lint (ruff), test (pytest), type check (mypy or pyright) | 1h | 1.7 | Matrix: Python 3.10, 3.11, 3.12. macOS + Windows. |
| 5.4 | **PyPI publish pipeline** — GitHub Actions on tag push, build sdist + wheel, publish to PyPI | 1h | 5.3 | Use `trusted publishers` (OIDC). Test with TestPyPI first. |

**Stage 5 verification**: Fresh `pip install zhi` on macOS + Windows, full workflow.

---

## Dependency Graph

```
Stage 1 (foundation)
  1.1 ──> 1.2 ──> 1.3
                  1.4 ──> 1.5
           1.6
           1.7 (after 1.2-1.6)

Stage 2 (core experience) — depends on Stage 1
  2.1 ──> 2.2
  2.3 ──> 2.4
  2.3 ──> 2.5, 2.6 ──> 2.7, 2.8
  1.4 + 2.1-2.4 ──> 2.9 ──> 2.10

Stage 3 (extended tools) — depends on Stage 2
  2.3 ──> 3.1, 3.2, 3.3 (parallel)
  3.1 + 2.7 ──> 3.4

Stage 4 (skills) — depends on Stage 2
  4.1 ──> 4.2 ──> 4.3, 4.4, 4.5
  4.1 ──> 4.6 ──> 4.7
  (can start Stage 4 while Stage 3 is in progress — independent)

Stage 5 (polish) — depends on Stages 1-4
  All ──> 5.1, 5.2, 5.3, 5.4
```

**Critical path**: 1.1 -> 1.2 -> 1.4 -> 2.3 -> 2.4 -> 2.9 -> 2.10 -> 4.4 -> 5.1

**Parallelism opportunities**:
- Stage 3 tools (3.1, 3.2, 3.3) can be built in parallel
- Stage 3 and Stage 4 can proceed concurrently (skills don't depend on OCR/shell/web tools existing)
- UI work (2.1, 2.2) can proceed in parallel with tool work (2.3-2.8)

---

## Gaps, Risks & Missing Pieces

### GAP-1: No API error handling / retry strategy
**Severity**: High
**Issue**: The plan has no mention of handling API failures — network errors, rate limits (429), server errors (500/503), token limits exceeded, or invalid API key after initial setup.
**Impact**: The CLI will crash or hang on any transient API failure. Users in China (primary audience for Zhipu) may face unstable connections.
**Recommendation**: Add exponential backoff retry with jitter for transient errors (429, 500, 503, network timeouts). Max 3 retries. Fail fast on 401/403 with "check your API key" message.

### GAP-2: No logging infrastructure
**Severity**: Medium
**Issue**: No mention of logging. When something goes wrong, there's no way to diagnose it.
**Impact**: Support/debugging will be painful. Users will report "it didn't work" with no details.
**Recommendation**: Add structured logging to `~/.zhi/logs/`. Default level INFO for file, WARNING for console. Debug mode via `--debug` flag or `ZHI_DEBUG=1`.

### GAP-3: No conversation persistence / session recovery
**Severity**: Medium
**Issue**: If the terminal crashes or user accidentally closes it, the entire conversation is lost. No way to resume.
**Impact**: Long skill-creation sessions or complex multi-step tasks are fragile.
**Recommendation**: Auto-save conversation to `~/.zhi/sessions/<timestamp>.json`. Add `/history` command to list recent sessions and `/resume` to continue one. Low priority but high user value.

### GAP-4: No token counting or cost awareness
**Severity**: Medium
**Issue**: Users have no visibility into how many tokens they're using or what it costs. GLM-5 is "expensive" but how expensive?
**Impact**: Users may be surprised by bills. Friends who install it might run up costs without realizing.
**Recommendation**: Track token usage per session (from API response). Display at exit: "Session used X tokens (~$Y)". Add `/usage` command. Optional per-session or daily budget limit.

### GAP-5: No graceful degradation when API is unreachable
**Severity**: Medium
**Issue**: If the Zhipu API is down, the CLI is completely useless — even for listing skills or reading help.
**Impact**: Users see a crash instead of a helpful message.
**Recommendation**: Slash commands must always work (they're local). Only AI-dependent operations should fail gracefully with a clear message: "Cannot reach Zhipu API. Check your connection. Local commands (/skill list, /help) still work."

### GAP-6: No input validation on file paths from model
**Severity**: High
**Issue**: The model may hallucinate file paths or try to read/write outside expected directories. The plan mentions `zhi-output/` but doesn't describe path sanitization.
**Impact**: Security risk — model could potentially read sensitive files or write outside the output directory.
**Recommendation**: `file_write` must validate output path is within `zhi-output/` (or skill-configured directory). `file_read` should have an allowlist or working-directory scope. Reject absolute paths or `..` traversal.

### GAP-7: No streaming for tool outputs
**Severity**: Low
**Issue**: Tool execution (especially OCR, web fetch, shell) may take a while with no progress indication.
**Impact**: User thinks the CLI is frozen.
**Recommendation**: Show a Rich spinner/progress bar during tool execution. For OCR polling, show "OCR processing... (elapsed: Xs)".

### GAP-8: OCR async polling not detailed
**Severity**: Medium
**Issue**: The plan mentions OCR via `/v4/layout_parsing` but this is an async API. The flow (submit -> poll -> retrieve) is not specified.
**Impact**: Implementer may miss the async nature and build a broken OCR tool.
**Recommendation**: Document the OCR flow explicitly: POST file -> get task_id -> poll `/v4/async-result/{id}` every 2s -> return result on COMPLETED. Timeout after 60s.

### GAP-9: No `--version` flag
**Severity**: Low
**Issue**: No way to check installed version.
**Recommendation**: Add `zhi --version` from `__init__.__version__` (read from pyproject.toml via importlib.metadata).

### GAP-10: Skill YAML injection risk
**Severity**: Medium
**Issue**: If users share skill YAML files, a malicious skill could include `shell` in its tools list and run arbitrary commands.
**Impact**: Running a shared skill could execute malicious shell commands.
**Recommendation**: When loading a skill from an untrusted source, warn the user about which tools it uses (especially `shell`). Add a "trust prompt" on first run of a new skill: "This skill uses: shell, file_write. Allow? [y/n]".

### GAP-11: No max output size for tools
**Severity**: Medium
**Issue**: `file_read`, `web_fetch`, and `shell` could return huge outputs that blow the context window.
**Impact**: API call fails with token limit error, or costs spike.
**Recommendation**: Cap tool output at a configurable limit (e.g., 50KB). Truncate with "[truncated, showing first 50KB of 2MB]".

### GAP-12: No `file_write` data format contract
**Severity**: High
**Issue**: The plan says the model says "write data to output.xlsx" and the tool "handles format conversion." But what data format does the model send? A JSON string? A list of dicts? Markdown table?
**Impact**: This is the most likely place for bugs. The model and tool need a clear contract.
**Recommendation**: Define explicit format contracts in the tool's JSON Schema description:
- `.xlsx`: expects `{"sheets": [{"name": "Sheet1", "headers": [...], "rows": [[...]]}]}`
- `.docx`: expects `{"content": "markdown string"}`
- `.csv`: expects `{"headers": [...], "rows": [[...]]}`
- `.json`: pass-through

---

## Architecture Improvements

### AUDIT-ARCH-1: Add a `Context` object for request-scoped state

Currently the plan passes individual values (model, messages, tools, on_permission) through functions. A `Context` dataclass would be cleaner:

```python
@dataclass
class Context:
    config: Config
    client: Client
    model: str
    tools: list[BaseTool]
    permission_mode: PermissionMode
    conversation: list[dict]
    session_tokens: int = 0
```

Pass `Context` to the agent loop and REPL. Makes it easy to add features (token tracking, logging) without changing function signatures everywhere.

### AUDIT-ARCH-2: Event-based tool execution hooks

Instead of hardcoding UI updates in the agent loop, emit events that the UI layer subscribes to:

```python
# In agent loop
self.emit("tool_start", tool=tool, args=args)
result = tool.execute(**args)
self.emit("tool_end", tool=tool, result=result)

# UI subscribes
agent.on("tool_start", lambda e: console.print(f"Running {e.tool.name}..."))
```

This decouples the agent logic from UI, making testing easier and enabling future features like logging, metrics, or webhook notifications.

### AUDIT-ARCH-3: Structured tool results

Tools should return a typed `ToolResult` instead of raw strings:

```python
@dataclass
class ToolResult:
    content: str           # text to send back to model
    display: str | None    # optional different display for user (e.g., truncated)
    artifacts: list[Path]  # files created (for tracking)
    tokens_estimate: int   # rough token count of content
```

This enables better UI (show user a summary, send model full data), artifact tracking, and token awareness.

### AUDIT-ARCH-4: Plugin-ready tool architecture

The current `tools/__init__.py` registry is good. Extend it to support external tool packages:

```python
# In pyproject.toml of a third-party package:
[project.entry-points."zhi.tools"]
my_tool = "my_package.tools:MyTool"
```

This allows the ecosystem to grow without forking zhi. Not needed for v1 but design the registry to not preclude it.

### AUDIT-ARCH-5: Separate `client.py` into sync and streaming paths

The plan's `client.chat()` needs to handle both:
1. **Streaming** (interactive mode) — yield tokens as they arrive for live display
2. **Non-streaming** (skill execution) — return complete response

Design the client with both paths from the start rather than retrofitting streaming later:

```python
def chat(self, ...) -> ChatResponse:
    """Non-streaming. Returns complete response."""

def chat_stream(self, ...) -> Iterator[ChatChunk]:
    """Streaming. Yields chunks for live display."""
```

### AUDIT-ARCH-6: Config validation layer

Add a Pydantic model (or simple dataclass with validation) for config:

```python
@dataclass
class ZhiConfig:
    api_key: str                    # required
    default_model: str = "glm-5"   # validated against known models
    output_dir: str = "zhi-output"
    max_turns: int = 30
    log_level: str = "INFO"

    def validate(self):
        if not self.api_key:
            raise ConfigError("API key required")
        if self.default_model not in KNOWN_MODELS:
            warn(f"Unknown model: {self.default_model}")
```

### AUDIT-ARCH-7: Conversation message types

Use an enum or typed dicts for message roles instead of raw strings:

```python
class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
```

Prevents typos and makes the codebase more navigable.

---

## Missing Components

### COMP-1: API retry logic with exponential backoff

```python
# client.py
async def _call_with_retry(self, fn, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except (RateLimitError, ServerError, ConnectionError) as e:
            if attempt == max_retries:
                raise
            wait = min(2 ** attempt + random.uniform(0, 1), 30)
            logger.warning(f"Retry {attempt+1}/{max_retries} in {wait:.1f}s: {e}")
            await asyncio.sleep(wait)
```

### COMP-2: Rate limiting awareness

Track requests per minute. If approaching Zhipu's rate limit, proactively slow down rather than hitting 429 errors. Display a note: "Slowing down to stay within API rate limits."

### COMP-3: Config migration

When config schema changes between versions, provide automatic migration:

```python
def migrate_config(config: dict, from_version: str, to_version: str) -> dict:
    """Apply sequential migrations."""
```

### COMP-4: Ctrl+C / signal handling

The plan mentions Ctrl+C but doesn't detail implementation. Needs:
- `signal.signal(signal.SIGINT, handler)` to catch interrupts
- Cancel the current API streaming call
- Preserve messages up to the interruption point
- Return to prompt cleanly (no stack trace)

### COMP-5: Output directory management

- Auto-create `zhi-output/` on first write
- Configurable via `config.yaml` and per-skill YAML
- Add `/output` command to open the output directory in file manager
- Track files created in current session for summary at exit

### COMP-6: Model registry

Maintain a list of known Zhipu models with metadata:

```python
MODELS = {
    "glm-5": {"tier": "premium", "supports_thinking": True, "supports_tools": True},
    "glm-4-flash": {"tier": "economy", "supports_thinking": False, "supports_tools": True},
    "glm-4-air": {"tier": "economy", "supports_thinking": False, "supports_tools": True},
}
```

Validate `/model` commands against this. Warn if user picks a model without tool support.

### COMP-7: Test fixtures and mocks

Create a shared test infrastructure:
- `conftest.py` with mock API client, temp config directory, sample files
- Fixture for creating temp skill YAML files
- Mock tool registry for testing agent loop in isolation
- Sample PDF/image fixtures for OCR tests (small, committed to repo)

### COMP-8: Type hints throughout

The plan's code snippets lack type hints. For a Python project in 2026, full type hints with `pyright` or `mypy` checking should be standard from day one. Add `py.typed` marker for downstream consumers.

---

## Summary of Priorities

**Must-have for v1 (blocks usability)**:
- GAP-1: API retry/error handling
- GAP-5: Graceful degradation
- GAP-6: File path validation/sanitization
- GAP-11: Tool output size limits
- GAP-12: file_write data format contract
- COMP-4: Ctrl+C signal handling

**Should-have for v1 (significantly improves experience)**:
- GAP-2: Logging
- GAP-4: Token/cost tracking
- GAP-7: Tool execution progress
- GAP-8: OCR async flow documentation
- AUDIT-ARCH-1: Context object
- AUDIT-ARCH-5: Streaming vs non-streaming client
- AUDIT-ARCH-6: Config validation

**Nice-to-have (can defer to v1.1)**:
- GAP-3: Session persistence/resume
- GAP-10: Skill trust prompts
- AUDIT-ARCH-2: Event-based hooks
- AUDIT-ARCH-3: Structured tool results
- AUDIT-ARCH-4: Plugin architecture
- COMP-2: Rate limiting
- COMP-3: Config migration
