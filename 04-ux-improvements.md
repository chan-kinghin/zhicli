# UX Improvements for `zhi` CLI

## 1. First-Run Experience

### 1.1 Onboarding Wizard Flow

**Current**: Plan mentions a config wizard on first run but does not detail the flow.

**Proposed flow**:

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

**Key design decisions**:
- 3 steps maximum. Users abandon wizards longer than 5 steps.
- API key validation is immediate. Shows which models are available on their plan.
- Sensible defaults with Enter-to-accept. Power users skip through in seconds.
- Optional demo skill run. Shows real value in under 10 seconds.
- Wizard only runs once. Re-run with `zhi --setup` or `zhi config reset`.

| Impact | Effort | Stage |
|--------|--------|-------|
| High | Low | Stage 1 |

### 1.2 API Key Validation

**Proposed**:
- On key entry, make a lightweight API call (e.g., list available models) to confirm validity.
- If invalid: clear message with common fixes ("Did you copy the full key? Keys start with `sk-`").
- If valid but rate-limited plan: warn about limits upfront.
- Store key in `~/.zhi/config.yaml` with file permissions `600` (owner-only read/write).
- Support `ZHI_API_KEY` env var as override (document in help text).

| Impact | Effort | Stage |
|--------|--------|-------|
| High | Low | 1 |

### 1.3 Sample Skill Demo

**Proposed**:
- Bundle 2 builtin skills (`summarize`, `translate`) with a tiny sample input text (~100 words).
- During onboarding, offer to run `summarize` on the sample to prove the tool works.
- Takes <5 seconds with GLM-4-flash. User sees the full pipeline: input -> model call -> file output.
- If the demo fails (network issue, API error), show a friendly message and continue setup. Do not block onboarding on demo success.

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Low | 1 |

---

## 2. REPL UX

### 2.1 Input History

**Current**: Plan lists `prompt_toolkit` as a dependency, which supports history natively.

**Proposed**:
- Persist history to `~/.zhi/history.txt` (configurable, max 10,000 entries).
- Up/Down arrow keys navigate history (standard readline behavior).
- Ctrl+R for reverse history search (type substring, find matching past commands).
- History excludes sensitive data: do not persist lines containing `api_key`, `password`, `token`, `secret`.
- `/history clear` command to wipe history file.

| Impact | Effort | Stage |
|--------|--------|-------|
| High | Low | 2 |

### 2.2 Tab Completion

**Proposed completions**:

| Context | Completes |
|---------|-----------|
| `/` then Tab | All slash commands: `/run`, `/skill`, `/auto`, `/approve`, etc. |
| `/run ` then Tab | Available skill names from builtin + user directory |
| `/skill ` then Tab | Subcommands: `list`, `new`, `edit`, `delete` |
| `/model ` then Tab | Available model names: `glm-5`, `glm-4-flash`, etc. |
| Any position with path-like text | File paths (using `prompt_toolkit`'s `PathCompleter`) |

**Implementation**: Use `prompt_toolkit`'s `NestedCompleter` or a custom `Completer` subclass. Completions show inline (fish-style ghost text) rather than a dropdown, to keep the interface clean.

| Impact | Effort | Stage |
|--------|--------|-------|
| High | Medium | 2 |

### 2.3 Multi-Line Input

**Proposed**:
- Backslash (`\`) at end of line continues to next line (standard shell convention).
- Alternative: triple backtick (```) to enter/exit multi-line mode (familiar from Markdown).
- Visual indicator: prompt changes from `You: ` to `...  ` on continuation lines.
- Paste detection: `prompt_toolkit` auto-detects multi-line paste and handles it as a single input.

```
You: Here is my prompt that spans \
...  multiple lines because it is \
...  a complex instruction
```

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Low | 2 |

### 2.4 File Path Autocomplete & Drag-and-Drop

**Proposed**:
- File path autocomplete via `prompt_toolkit`'s path completer when input contains `/` or `./` or `~/`.
- Terminal drag-and-drop: most modern terminals (iTerm2, Windows Terminal, Ghostty) emit file paths when files are dragged in. `prompt_toolkit` handles this natively since the path appears as typed text.
- Show file type icon/label after path resolution: `report.pdf (PDF, 240KB)`.
- Validate file exists before sending to agent. If not found, prompt: "File not found. Did you mean [closest match]?"

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Low | 2 |

### 2.5 Multimodal File Input (Drag-and-Drop)

**Current state**: Section 2.4 covers file path autocomplete and notes that "drag-and-drop from terminal works natively." This needs expansion into a full multimodal input feature.

**Proposed UX**:

Users drag files directly into the terminal. The CLI auto-detects file type and routes processing:

```
You: [drags invoice.pdf from Desktop]
  → invoice.pdf (PDF, 2.3MB)
  Processing with OCR...

You: [drags photo.jpg from Desktop]
  → photo.jpg (JPEG, 4.1MB)
  Sending to GLM vision...

You: [drags report.xlsx and summary.docx]
  → report.xlsx (Excel, 156KB) — OCR text extraction
  → summary.docx (Word, 89KB) — OCR text extraction
```

**File type routing:**

| File Type | Extensions | Route | Tool |
|-----------|-----------|-------|------|
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` | GLM vision API (multimodal chat) | New: `image_input` |
| PDFs | `.pdf` | Zhipu OCR API | Existing: `ocr` |
| Office docs | `.xlsx`, `.docx` | OCR for text extraction | Existing: `ocr` |
| Text files | `.txt`, `.md`, `.csv`, `.json`, `.yaml` | Direct read | Existing: `file_read` |

**Input safety:**
- File size limits: 10MB for images (auto-resize to 2048px max dimension), 20MB for PDFs, 100KB for text
- File type validation: reject executables (`.exe`, `.sh`, `.bat`, `.app`, `.dmg`)
- **File Safety Guarantee**: Input files are NEVER modified or deleted — only read or uploaded for processing

**Implementation notes:**
- Terminal drag-and-drop emits file paths as pasted text — `prompt_toolkit` handles this natively
- Multiple files can be dropped simultaneously (one path per line)
- Auto-detect via file extension, with fallback to `mimetypes.guess_type()`
- Images for vision API: auto-resize to max 2048px dimension, base64-encode, attach to chat message
- Show file metadata on detection: name, type, size — before processing begins
- Large images (>10MB) are auto-resized; large PDFs (>20MB) are rejected with a helpful message

| Impact | Effort | Stage |
|--------|--------|-------|
| High | Medium | Stage 3 (new image_input tool) + Stage 2 (path detection in REPL) |

---

## 3. Output UX

### 3.1 Progress Indicators

**Current**: Plan shows emoji-based step indicators (`OCR...`, `Write...`). Good start.

**Proposed enhancements**:
- **Spinner for model calls**: Use Rich's `Spinner` while waiting for LLM response. Show elapsed time.
- **Streaming tokens**: Stream model output token-by-token using Rich's `Live` display. Show a cursor blinking at the end.
- **Tool execution progress**: Show `[1/3] OCR: report_v1.pdf...` with a progress bar for multi-step operations.
- **Thinking mode display**: Render thinking text in dim/italic style (as noted in plan). Use Rich's `Padding` to indent thinking text.
- **Final summary line**: After a multi-step operation, show a one-line summary: `Done: 3 files processed, 1 file written (2.3s)`.

```
You: Compare these two reports

Thinking...
  These are PDF files, I need to OCR them first, then compare content.

[1/3] OCR: report_v1.pdf (2,340 chars)
[2/3] OCR: report_v2.pdf (2,518 chars)
[3/3] Writing comparison.xlsx

Done: 2 files read, 1 file written (4.1s)
  -> zhi-output/comparison.xlsx (12KB)
```

| Impact | Effort | Stage |
|--------|--------|-------|
| High | Medium | 2 |

### 3.2 Structured Error Messages

**Proposed format** for all errors:

```
Error: Could not connect to Zhipu API
  Reason: Connection timed out after 30s
  Try:
    1. Check your internet connection
    2. Verify API status at status.bigmodel.cn
    3. Run `zhi config show` to confirm your API key
```

**Rules**:
- Every error has three parts: **what** happened, **why** (if known), and **what to try**.
- Use Rich's `Panel` with red border for errors, yellow for warnings.
- Never show raw stack traces to the user. Log full traces to `~/.zhi/logs/` for debugging.
- Common error codes get custom messages (see Section 6 for full catalog).

| Impact | Effort | Stage |
|--------|--------|-------|
| High | Medium | 2, 5 |

### 3.3 Color Themes

**Proposed**:
- Ship with 2 built-in themes: `default` (for dark terminals) and `light` (for light terminals).
- Auto-detect terminal background if possible (some terminals expose this via `\e]11;?\a` escape sequence).
- Theme controls: `zhi config set theme light` or `zhi config set theme dark`.
- Theme defines colors for: user input, AI response, thinking text, tool output, errors, warnings, success, dimmed text.
- `--no-color` flag and `NO_COLOR` env var support (see Section 5).

| Impact | Effort | Stage |
|--------|--------|-------|
| Low | Medium | 5 |

### File Safety Guarantee

`zhi` makes the following guarantees about the user's filesystem:

- **Never deletes**: No file deletion capability exists. `/skill delete` only removes zhi's own skill YAML files.
- **Never modifies**: Existing files are never changed. `file_write` only creates new files. Overwrites always require confirmation, even in auto mode.
- **Scoped writes**: All output goes to `./zhi-output/`. Path traversal is rejected. Symlinks are resolved.
- **Shell always confirms**: The shell tool requires confirmation for every command regardless of mode. Destructive commands get extra warnings.
- **Read-only input**: Dragged/imported files are only read or uploaded — never modified.

---

## 4. Skill UX

### 4.1 Skill Discovery & Sharing

**Proposed** (phased approach):

**Phase 1 (Stage 4)**: Local skill management
- `/skill list` shows name, description, model, last-used date.
- `/skill show <name>` displays full YAML with syntax highlighting.
- `/skill edit <name>` opens the YAML in `$EDITOR` (or falls back to inline editing).
- `/skill delete <name>` with confirmation prompt.
- Skills stored in `~/.zhi/skills/` (user) and `src/zhi/skills/builtin/` (bundled).

**Phase 2 (Post-v1)**: Skill sharing
- `zhi skill export <name>` exports a self-contained `.zhi-skill` file (YAML + metadata).
- `zhi skill import <file-or-url>` imports a skill from file or URL.
- Optional: community skill index (a GitHub repo with curated skill YAMLs).
- Security: imported skills show their tool list and require explicit approval before first use.

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium (Phase 1), High (Phase 2) | Low (Phase 1), High (Phase 2) | 4, post-v1 |

### 4.2 Skill Versioning

**Proposed**:
- Add optional `version` field to skill YAML (semver string, e.g., `1.0.0`).
- When a skill is modified via `/skill edit` or re-created, auto-increment patch version.
- `/skill history <name>` shows version log (stored as git-style diffs or full copies in `~/.zhi/skills/<name>/versions/`).
- Rollback: `/skill rollback <name> <version>`.
- v1 scope: version field only, no history. History is post-v1.

| Impact | Effort | Stage |
|--------|--------|-------|
| Low | Medium | post-v1 |

### 4.3 Skill Templates

**Proposed**:
- `/skill new` offers template selection:
  ```
  Choose a template (or blank):
    1. blank        - Empty skill, you define everything
    2. file-process - Read files, transform, write output
    3. web-extract  - Fetch URLs, extract data, save results
    4. translate    - Translate text between languages
  ```
- Templates pre-fill `tools`, `system_prompt` skeleton, and `input` args.
- Users can create custom templates: `zhi skill save-template <skill-name>`.

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Low | 4 |

### 4.4 Skill Chaining

**Proposed**:
- Allow skills to call other skills via a `depends_on` or `chain` field in YAML:
  ```yaml
  name: invoice-report
  chain:
    - skill: ocr-extract
      input: $file1
    - skill: compare-docs
      input: [$prev.output, $file2]
  ```
- Simpler alternative for v1: pipe syntax in REPL: `/run ocr-extract invoice.pdf | /run summarize`.
- Recommendation: defer to post-v1. Complex to implement correctly and test. For v1, users can achieve similar results by describing the full workflow in a single skill's `system_prompt`.

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | High | post-v1 |

---

## 5. Accessibility

### 5.1 Screen Reader Support

**Proposed**:
- All output uses semantic text (not just ANSI escape codes for layout).
- Spinners and progress bars include text fallbacks: `[working...]` instead of a visual-only spinner.
- Rich supports `TERM=dumb` detection; ensure all output degrades to plain text gracefully.
- Test with VoiceOver (macOS) and NVDA (Windows) for basic compatibility.

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Medium | 5 |

### 5.2 No-Color Mode

**Proposed**:
- Respect the `NO_COLOR` environment variable (see no-color.org standard).
- `--no-color` CLI flag.
- `zhi config set color false` for persistent preference.
- When no-color is active: no ANSI codes, no emoji, plain text prefixes (`[ERROR]`, `[TOOL]`, `[DONE]`).

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Low | 2 |

### 5.3 Verbose / Debug Mode

**Proposed**:
- `--verbose` or `-v` flag shows: full API request/response payloads, tool execution details, timing for each step.
- `-vv` (double verbose) adds: raw HTTP headers, token counts, cost estimates.
- `/verbose` toggle in REPL to switch without restarting.
- Verbose output goes to stderr (or a log file) so it does not interfere with piped stdout.

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Low | 2 |

---

## 6. Error UX

### 6.1 Error Message Catalog

Every common failure should have a specific, actionable error message:

| Error | Message | Suggestions |
|-------|---------|-------------|
| Invalid API key | `Error: Invalid API key` | 1. Check key starts with `sk-`. 2. Regenerate at open.bigmodel.cn. 3. Run `zhi config set api_key <key>`. |
| Network unreachable | `Error: Cannot reach Zhipu API` | 1. Check internet connection. 2. Check if behind a proxy (`zhi config set proxy <url>`). 3. Try again in a few seconds. |
| Rate limited | `Error: Rate limit exceeded` | 1. Wait {retry_after} seconds. 2. Switch to a cheaper model: `/model glm-4-flash`. 3. Check your plan limits at open.bigmodel.cn. |
| Model unavailable | `Error: Model {name} is not available` | 1. Check available models: `/model list`. 2. Your plan may not include this model. |
| Malformed skill YAML | `Error: Invalid skill file "{name}.yaml"` | 1. {specific YAML parse error with line number}. 2. Check required fields: name, description, system_prompt, tools. 3. See example: `zhi skill show summarize`. |
| File not found | `Error: File not found: {path}` | 1. Check the path is correct. 2. Did you mean: {closest match}? 3. Use Tab to autocomplete file paths. |
| Permission denied (file) | `Error: Cannot read file: {path}` | 1. Check file permissions. 2. Try: `chmod +r {path}` (macOS/Linux). |
| Output dir not writable | `Error: Cannot write to {dir}` | 1. Check directory permissions. 2. Change output dir: `zhi config set output_dir <path>`. |
| Tool not allowed in skill | `Error: Skill "{name}" does not allow tool "{tool}"` | 1. Edit the skill to add the tool: `/skill edit {name}`. 2. Or use interactive mode (all tools available). |
| API timeout | `Error: API request timed out after {n}s` | 1. The model may be overloaded. Try again. 2. Switch to a faster model: `/model glm-4-flash`. 3. Check API status at status.bigmodel.cn. |
| Context too long | `Error: Conversation too long for model` | 1. Start a new conversation: `/reset`. 2. Use a model with larger context. |

**Implementation**:
- Each error is a dataclass with `code`, `message`, `suggestions`, `log_details`.
- Errors render via Rich `Panel` with red border.
- `log_details` (stack trace, raw response) written to `~/.zhi/logs/` but not shown to user.
- Suggestion #1 is always the most likely fix.

| Impact | Effort | Stage |
|--------|--------|-------|
| High | Medium | 2, 5 |

### 6.2 Automatic Retry with Backoff

**Proposed**:
- Transient errors (network timeout, 429 rate limit, 503 service unavailable) auto-retry up to 3 times.
- Exponential backoff: 1s, 3s, 9s.
- Show retry progress: `Retrying in 3s... (attempt 2/3)`.
- Non-transient errors (401 auth, 400 bad request, YAML parse) fail immediately with suggestions.

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Low | 2 |

---

## 7. Advanced Features

### 7.1 Conversation History (Save / Resume)

**Proposed**:
- Auto-save conversation to `~/.zhi/conversations/<timestamp>.json` on `/exit`.
- `/conversations` lists recent conversations with first-line preview.
- `/resume [id]` loads a previous conversation into the agent (messages array).
- `/reset` clears current conversation and starts fresh.
- Conversations expire after 30 days by default (configurable).

Inspired by: Open Interpreter's `--conversations` flag with arrow-key selection.

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Medium | post-v1 |

### 7.2 Piping stdin / Non-Interactive Mode

**Proposed**:
- `echo "summarize this" | zhi` reads from stdin, runs once, outputs to stdout, exits.
- `zhi -c "translate this text to Chinese"` one-shot mode (no REPL).
- `zhi run <skill> <files>` (without slash) as a direct CLI command, no REPL.
- Detect `isatty(stdin)` to auto-switch between interactive and pipe mode.
- Pipe mode: no color, no spinner, no prompt. Just output.
- Exit code: 0 on success, 1 on error.

```bash
# Pipeline examples
cat report.txt | zhi -c "summarize this"
zhi run translate README.md --to chinese > README_zh.md
ls *.pdf | xargs -I{} zhi run ocr-extract {}
```

| Impact | Effort | Stage |
|--------|--------|-------|
| High | Medium | 3 or 4 |

### 7.3 Conversation Export

**Proposed**:
- `/export md` exports current conversation as Markdown.
- `/export json` exports as raw JSON (messages array).
- Output goes to `./zhi-output/conversation-<timestamp>.md`.
- Useful for documentation, sharing results, or feeding into other tools.

| Impact | Effort | Stage |
|--------|--------|-------|
| Low | Low | 5 |

### 7.4 Cost Tracking

**Proposed**:
- Track token usage per conversation and per session.
- `/usage` shows: tokens in/out, estimated cost, model breakdown.
- Optional: show cost after each AI response in verbose mode.
- Persistent usage log in `~/.zhi/usage.json` for monthly tracking.

Inspired by: aider's token/cost tracking in its output.

| Impact | Effort | Stage |
|--------|--------|-------|
| Medium | Low | 5 |

---

## 8. Competitive Analysis

### 8.1 Patterns to Adopt from CLI Assistants

| Pattern | How zhi should adopt it | Priority |
|---------|------------------------|----------|
| **Zero-config project detection** | Auto-detect project type from cwd (has `package.json`? `pyproject.toml`?). Adjust system prompt context. | Medium |
| **Step-by-step narration** | Already in plan (emoji + tool names). Ensure every tool call is announced before execution. | High |
| **Tab to accept suggestions** | After AI proposes a plan or action, show `Press Tab to accept, Enter to modify`. | Medium |
| **Interrupt and redirect (Ctrl+C)** | Already in plan. Preserve conversation context on interrupt. | High |
| **IME support** | Use `prompt_toolkit` which handles CJK input correctly. Test with Chinese input specifically since zhi targets Chinese-speaking users. | High |
| **Permission mode toggle** | Already in plan (`/auto`, `/approve`). Match similar CLI tools' UX of clear mode indicator in prompt. | High |

### 8.2 Patterns to Adopt from Aider

| Pattern | How zhi should adopt it | Priority |
|---------|------------------------|----------|
| **Automatic git commits** | Not applicable for zhi (not a coding tool), but consider auto-saving skill changes with version tracking. | Low |
| **Repo map / context awareness** | When working with files, show the user which files are "in context" so they understand what the AI can see. | Medium |
| **Voice input** | Post-v1 consideration. Could be interesting for Chinese voice input. | Low |
| **Easy installation via uv** | Support `uv tool install zhi` for isolated Python environment. Document alongside `pip install`. | Medium |

### 8.3 Patterns to Adopt from Gemini CLI

| Pattern | How zhi should adopt it | Priority |
|---------|------------------------|----------|
| **Flicker-free rendering** | Use Rich's `Live` display for streaming. Avoid re-rendering entire output on each token. | High |
| **Tab to switch focus** | If zhi adds a split-pane view (e.g., output + input), Tab switching is useful. For v1 REPL, not needed. | Low |
| **Dynamic terminal tab title** | Set terminal title to `zhi - <current-skill>` or `zhi - chatting` via ANSI escape. | Low |
| **Plan mode** | zhi uses GLM-5's built-in thinking mode instead of a separate plan mode. This is simpler. Keep it. | N/A |
| **Theme auto-detection** | Detect dark/light terminal background and pick theme automatically. | Low |
| **Mouse click in input** | `prompt_toolkit` supports this. Enable it. | Low |

### 8.4 Patterns to Adopt from Open Interpreter

| Pattern | How zhi should adopt it | Priority |
|---------|------------------------|----------|
| **Conversation save/resume** | `/conversations` to list and resume past sessions. Arrow-key selection. | Medium |
| **%undo command** | `/undo` removes last exchange (user message + AI response) from context. Useful when AI misunderstands. | Medium |
| **%reset command** | `/reset` clears conversation but keeps session config. | High |
| **Natural language for everything** | zhi already does this. Non-slash input goes to AI. Good. | N/A |

---

## 9. Priority Summary

### Must-Have for v1 (Stages 1-4)

| Improvement | Stage | Impact | Effort |
|-------------|-------|--------|--------|
| Onboarding wizard (3-step) | 1 | High | Low |
| API key validation | 1 | High | Low |
| Input history (persistent) | 2 | High | Low |
| Tab completion (slash commands + skills + paths) | 2 | High | Medium |
| Progress indicators (spinner, streaming, step counter) | 2 | High | Medium |
| Structured error messages (catalog) | 2 | High | Medium |
| No-color mode (`NO_COLOR`, `--no-color`) | 2 | Medium | Low |
| Verbose mode (`-v`, `/verbose`) | 2 | Medium | Low |
| Auto-retry with backoff | 2 | Medium | Low |
| Multi-line input | 2 | Medium | Low |
| `/reset` command | 2 | High | Low |
| `/undo` command | 2 | Medium | Low |
| Skill templates | 4 | Medium | Low |
| Skill management (`show`, `edit`, `delete`) | 4 | Medium | Low |
| Non-interactive mode (`-c`, pipe, `run` without `/`) | 3-4 | High | Medium |
| CJK/IME input testing | 2 | High | Low |

### Nice-to-Have for v1 (Stage 5 - Polish)

| Improvement | Stage | Impact | Effort |
|-------------|-------|--------|--------|
| Color themes (dark/light) | 5 | Low | Medium |
| Cost/usage tracking | 5 | Medium | Low |
| Conversation export | 5 | Low | Low |
| Screen reader fallbacks | 5 | Medium | Medium |
| Sample skill demo in onboarding | 1 | Medium | Low |
| File-not-found suggestions (closest match) | 5 | Low | Low |

### Post-v1

| Improvement | Impact | Effort |
|-------------|--------|--------|
| Skill sharing (export/import/community index) | High | High |
| Conversation save/resume | Medium | Medium |
| Skill versioning with history | Low | Medium |
| Skill chaining (pipe syntax) | Medium | High |
| Voice input | Low | High |
| Project/context awareness | Medium | Medium |

---

## 10. Design Principles

Based on competitor analysis and the goals of zhi, these principles should guide all UX decisions:

1. **Instant value**: First run to first useful output in under 60 seconds. The onboarding wizard and sample demo achieve this.

2. **Progressive disclosure**: Start simple (type a message, get a response). Discover slash commands, skills, and advanced features as needed. Never overwhelm new users.

3. **Transparency over magic**: Always show what the agent is doing (which tool, which file, which model). Users who see the process trust the tool more.

4. **Fail helpfully**: Every error message tells the user what to do next. No dead ends.

5. **Respect the terminal**: Work with terminal conventions (Ctrl+C to cancel, Up for history, Tab to complete). Do not fight muscle memory.

6. **Chinese-first internationalization**: Since the target audience includes Chinese-speaking users, ensure CJK text rendering, IME input, and Chinese-language error messages/help text are first-class concerns (not afterthoughts).

7. **Scriptable by default**: Everything that works in the REPL should also work non-interactively. `zhi -c "..."` and `zhi run skill file` are essential for power users and automation.
