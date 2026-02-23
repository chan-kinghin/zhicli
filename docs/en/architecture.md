# Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                             │
│  cli.py ─── argument parsing, mode dispatch                  │
│  repl.py ── interactive REPL with slash commands             │
│  ui.py ──── Rich-based terminal output                       │
├─────────────────────────────────────────────────────────────┤
│                      Agent Layer                             │
│  agent.py ── agent loop (LLM → tools → LLM → ...)           │
│  client.py ─ Zhipu API client                                │
│  models.py ─ model registry (GLM-5, GLM-4-flash, GLM-4-air) │
├─────────────────────────────────────────────────────────────┤
│                      Tool Layer                              │
│  tools/base.py ──── BaseTool ABC + Registrable protocol      │
│  tools/__init__.py ─ ToolRegistry + factory functions         │
│  tools/file_read.py, file_write.py, file_list.py             │
│  tools/ocr.py, shell.py, web_fetch.py, skill_create.py      │
│  tools/skill_tool.py ── SkillTool wrapper for nested agents  │
├─────────────────────────────────────────────────────────────┤
│                     Skill Layer                              │
│  skills/loader.py ── YAML parsing + validation               │
│  skills/__init__.py ─ discovery (builtin + user directories) │
│  skills/builtin/*.yaml ── 15 built-in skill configurations   │
├─────────────────────────────────────────────────────────────┤
│                    Support Layer                             │
│  config.py ── platform-specific config (YAML + env vars)     │
│  i18n.py ──── bilingual string catalog + language preamble   │
│  errors.py ── structured error types                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Dual-Model Architecture

zhi uses two models with different cost-performance characteristics:

| Model | Role | Tier | Thinking | Use case |
|-------|------|------|----------|----------|
| **GLM-5** | Interactive chat | Premium | Yes | Conversations, complex reasoning |
| **GLM-4-flash** | Skill execution | Economy | No | Batch tasks, document processing |

**Why two models?**

- Interactive chat benefits from GLM-5's deeper reasoning and thinking mode
- Skills (summarize, translate, extract) run deterministic workflows where GLM-4-flash is sufficient
- GLM-4-flash costs roughly 10% of GLM-5, making batch operations cost-effective
- Users can override this per-session with `/model` or per-skill in YAML configs

---

## Agent Loop

The core of zhi is an agentic loop in `agent.py` that iterates between the LLM and tools:

```
User Input → Context → LLM (with tool schemas)
                         │
                    Tool Calls?
                    │ Yes          │ No
                    ▼              ▼
              Execute Tools    Return Response
              Append Results
              Loop ←──────┘
```

### Context

The `Context` dataclass holds all state for a single agent run:

```python
@dataclass
class Context:
    config: Any              # ZhiConfig instance
    client: ClientLike       # Zhipu API client
    model: str               # Active model name
    tools: dict[str, ToolLike]  # Available tools
    tool_schemas: list[dict]    # OpenAI-format function schemas
    permission_mode: PermissionMode  # approve or auto
    conversation: list[dict]        # Message history
    session_tokens: int = 0         # Cumulative token count
    max_turns: int = 30             # Turn limit
    thinking_enabled: bool = True   # Extended reasoning
    # Callbacks for UI integration
    on_stream, on_thinking, on_tool_start, on_tool_end,
    on_permission, on_waiting
```

### Loop Behavior

1. Send conversation + tool schemas to LLM
2. If the response contains tool calls:
   - Check permissions (risky tools in approve mode)
   - Execute each tool, cap output at 50KB
   - Append results to conversation
   - Loop back to step 1
3. If the response is text-only, return it (agent is done)
4. If `max_turns` is reached, return `None`

### Permission Check

```
Tool is risky?
  │ No → Execute immediately
  │ Yes
  ▼
Mode is approve?
  │ No (auto) → Execute immediately (except shell)
  │ Yes
  ▼
Call on_permission callback → User approves? → Execute
                              User denies?  → Return "Permission denied"
```

!!! info "Shell is always risky"
    The `shell` tool has `risky = True` and the agent loop always checks permissions for it, regardless of the permission mode. This is enforced at the tool level.

---

## Tool Registry

### BaseTool ABC

All built-in tools inherit from `BaseTool`:

```python
class BaseTool(ABC):
    name: ClassVar[str]           # Unique identifier
    description: ClassVar[str]    # Description for the LLM
    parameters: ClassVar[dict]    # JSON Schema for parameters
    risky: ClassVar[bool] = False # Requires permission?

    @abstractmethod
    def execute(self, **kwargs) -> str: ...

    def to_function_schema(self) -> dict: ...
```

### ToolRegistry

The registry manages tool instances and generates schemas:

| Method | Description |
|--------|-------------|
| `register(tool)` | Add a tool (raises `ValueError` on duplicate names) |
| `get(name)` | Look up a tool by name |
| `list_tools()` | Return all registered tools |
| `filter_by_names(names)` | Subset of tools by name list |
| `to_schemas()` | Export all tools as OpenAI-format function schemas |
| `to_schemas_filtered(names)` | Export schemas for a subset of tools |

### Registration Order

```python
# 1. File-based tools (no external deps)
registry = create_default_registry()
# → file_read, file_write, file_list, web_fetch

# 2. Tools requiring runtime deps
registry.register(OcrTool(client=client))
registry.register(ShellTool(permission_callback=...))

# 3. Skill tools (discovered from YAML)
skills = discover_skills()
register_skill_tools(registry, skills, client)
# → skill_summarize, skill_translate, ...
```

---

## Skill System

### Skill Configuration

Skills are defined as YAML files with this structure:

```yaml
name: summarize
description: Summarize a text file or document
model: glm-4-flash
system_prompt: |
  You are a concise summarization assistant...
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

### SkillConfig Dataclass

```python
@dataclass
class SkillConfig:
    name: str
    description: str
    system_prompt: str
    tools: list[str]
    model: str = "glm-4-flash"
    max_turns: int = 15
    input_args: list[dict] = field(default_factory=list)
    output_description: str = ""
    output_directory: str = "zhi-output"
    source: str = ""  # "builtin" or "user"
```

### Skill Discovery

Skills are discovered from two directories:

1. **Builtin**: `src/zhi/skills/builtin/*.yaml` (shipped with the package)
2. **User**: User-defined directory (overrides builtins with same name)

Corrupted YAML files are skipped with a warning.

### Composite Skills

Composite skills reference other skills as tools. When a skill lists `analyze` in its tools, the system resolves it as `skill_analyze` and wraps it as a `SkillTool`:

```yaml
# contract-review.yaml
tools:
  - file_read
  - ocr
  - file_write
  - analyze      # → resolved as skill_analyze
  - compare      # → resolved as skill_compare
  - proofread    # → resolved as skill_proofread
```

### Recursion Protection

Nested skill execution has three safety mechanisms:

| Mechanism | Limit | Behavior |
|-----------|-------|----------|
| **Cycle detection** | N/A | Blocks if skill name appears in current call chain |
| **Depth limit** | 3 levels | Blocks execution beyond max depth |
| **Max turns** | Per-skill | Each nesting level has its own turn limit |

---

## i18n System

### Language Preamble

Every skill prompt is prepended with a language preamble:

> IMPORTANT: Always respond in the same language as the input document. If the document or user input is in Chinese, your ENTIRE output -- including all section headers, table headers, column names, labels, and structural elements -- MUST be in Chinese. Never mix languages in your response.

This ensures consistent output language across the entire skill chain, including nested composite skills.

### String Catalog

The UI uses a key-based string catalog with English and Chinese translations:

```python
t("repl.help")           # → English or Chinese help text
t("ui.confirm_rich",     # → "Allow file_write(path)?"
   tool="file_write",
   args="path")
```

### Language Resolution

```
Explicit set_language("zh") → "zh"
                             ↓ (if "auto")
ZHI_LANGUAGE env var → check for "zh" prefix
                             ↓ (not set)
LANG / LC_ALL env vars → check for "zh" prefix
                             ↓ (not set)
Default → "en"
```

---

## Security Model

### Output Isolation

All file writes go to `zhi-output/` (configurable). Original files are never modified.

| Check | Description |
|-------|-------------|
| Relative paths only | Absolute paths rejected |
| No traversal | `..` segments blocked |
| Symlink resolution | Resolved path must stay within output directory |
| No overwrite | Existing files cannot be replaced |

### Shell Safety

Three-tier command classification:

| Tier | Examples | Behavior |
|------|----------|----------|
| **Blocked** | `rm -rf /`, fork bomb, `dd` to devices | Always rejected, no confirmation possible |
| **Destructive** | `rm`, `mv`, `chmod`, `sed -i`, `git reset --hard` | Extra warning + confirmation |
| **Standard** | `ls`, `wc`, `grep` | Standard confirmation |

Bypass patterns (`eval`, `bash -c`, `sh -c`, `/bin/rm`) are also blocked.

### SSRF Protection

The `web_fetch` tool blocks access to:

- `localhost` and known metadata endpoints
- Private IP ranges (RFC 1918)
- Loopback and link-local addresses

### Config Security

- Config file permissions: `0o600` (owner-only)
- API key stored in plain text (use `ZHI_API_KEY` env var for shared systems)
- Sensitive inputs excluded from REPL history
