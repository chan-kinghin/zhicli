# Success Metrics & KPIs for `zhi` CLI

Reference: `~/docs/plans/2026-02-23-zhi-cli-design.md`

---

## 1. Per-Stage Completion Criteria

### Stage 1: Scaffold + Config + Client

| Criterion | Definition of Done |
|-----------|-------------------|
| Package installable | `pip install -e .` succeeds; `zhi` entry point resolves without import errors |
| Config wizard | First run detects missing config, prompts for API key, saves to `~/.zhi/config.yaml` (macOS) or `%APPDATA%/zhi/config.yaml` (Windows) |
| Config reload | Editing `config.yaml` or setting `ZHI_API_KEY` env var is picked up on next launch without re-running wizard |
| Client connectivity | `client.chat()` sends a simple prompt to GLM-5 and returns a valid response object; non-200 responses raise typed exceptions |
| Error on bad key | Invalid API key produces a clear, single-line error message (not a stack trace) within 3 seconds |
| Tests | Unit tests for config load/save, env var fallback, client request/response parsing; all pass |

### Stage 2: REPL + Tools + Agent Loop

| Criterion | Definition of Done |
|-----------|-------------------|
| REPL functional | Launches, accepts input, responds, handles `/help`, `/exit` without errors |
| Slash commands | All 16 slash commands (`/run`, `/skill list`, `/skill new`, `/skill show`, `/skill edit`, `/skill delete`, `/auto`, `/approve`, `/think`, `/fast`, `/model`, `/reset`, `/undo`, `/usage`, `/help`, `/exit`) parse correctly; unknown commands show helpful error |
| Agent loop | Sends user message, receives streaming response, handles tool calls, respects `max_turns` |
| Permission modes | `/approve` prompts on risky tools; `/auto` skips prompts; mode persists across turns |
| file_write formats | Correctly produces `.xlsx`, `.docx`, `.csv`, `.json`, `.md`, `.txt` from structured data; output lands in `./zhi-output/` |
| Overwrite protection | Attempting to write an existing file triggers confirmation prompt in approve mode |
| Interrupt handling | Ctrl+C stops current operation, preserves conversation history, returns to prompt |
| Tests | Unit tests for REPL command parsing, tool registry, agent loop (mocked API), permission logic, file_write format detection |

### Stage 3: OCR + Shell + Web Tools

| Criterion | Definition of Done |
|-----------|-------------------|
| OCR tool | Accepts PDF/image path, calls `/v4/layout_parsing`, returns markdown text; errors on unsupported formats |
| Shell tool | Executes commands cross-platform, enforces timeout (default 30s), captures stdout+stderr |
| Web fetch | Fetches URL, extracts readable text, handles redirects and non-200 status |
| End-to-end | "OCR this invoice and save as Excel" completes without manual intervention (in auto mode) |
| Tests | Unit tests for each tool with mocked external calls; integration test for OCR-to-Excel pipeline |

### Stage 4: Skill System

| Criterion | Definition of Done |
|-----------|-------------------|
| YAML loading | Valid skill YAML parses without error; invalid YAML produces actionable error message pointing to the problem |
| Skill discovery | Finds skills in both `skills/builtin/` and `~/.zhi/skills/`; no duplicates; alphabetical listing |
| Skill creation | Conversational skill creation via `skill_create` tool produces valid YAML; saved skill is immediately runnable |
| `/run` execution | Runs skill with correct model (defaults to skill's `model` field), restricts to listed tools, respects `max_turns` |
| Two-model split | Interactive chat uses GLM-5; `/run` uses skill's model (e.g., GLM-4-flash); `--model` flag overrides |
| Builtin skills | `summarize` and `translate` work correctly out of the box |
| Tests | YAML validation tests (valid + 5 invalid cases), skill discovery tests, end-to-end skill create-and-run test |

### Stage 5: Polish + Publish

| Criterion | Definition of Done |
|-----------|-------------------|
| Error messages | All user-facing errors are single-line, actionable, and free of stack traces (unless `--debug` flag) |
| README | Covers: install, quickstart (< 2 min to first response), skill authoring guide, configuration reference |
| CI pipeline | GitHub Actions runs tests on Python 3.10+ across macOS and Windows; PyPI publish on tag |
| Fresh install | `pip install zhi` on a clean virtualenv completes and `zhi --help` works on both macOS and Windows |
| End-to-end | Full workflow (config, chat, OCR, skill create, skill run, skill list) succeeds on fresh install |

---

## 2. Performance Targets

| Metric | What to Measure | Target | How to Measure | Stage |
|--------|----------------|--------|---------------|-------|
| REPL startup time | Time from `zhi` command to input prompt ready | < 500ms (cold), < 300ms (warm) | `time zhi --benchmark-startup` (internal flag that exits after prompt ready); measure with `hyperfine` in CI | Stage 2 |
| Tool execution latency (local) | Time for `file_read`, `file_write`, `file_list` to complete | < 100ms for files under 10MB | Instrument `tool.execute()` with timing decorator; log p50/p95 | Stage 2 |
| Tool execution latency (API) | Time for `ocr` tool round-trip | < 5s for a single-page PDF | Instrument API call timing; log in debug mode | Stage 3 |
| Streaming first-token time | Time from sending request to first streamed character displayed | < 800ms on stable connection | Measure delta between `client.chat()` call and first `on_chunk` callback | Stage 2 |
| Skill load time | Time to parse YAML and initialize skill config | < 50ms per skill | Benchmark `loader.load()` with 20 skills | Stage 4 |
| Skill discovery time | Time to scan all skill directories and list available skills | < 200ms with 50 skills installed | Benchmark `/skill list` command | Stage 4 |
| file_write (xlsx) | Time to write a 1000-row Excel file | < 2s | Benchmark with synthetic data in tests | Stage 2 |
| Memory usage (idle REPL) | RSS after startup, before any query | < 50MB | `resource.getrusage()` or `psutil.Process().memory_info().rss` | Stage 2 |
| Memory usage (peak) | RSS during a 20-turn conversation | < 200MB | Monitor during integration test | Stage 2 |

---

## 3. Reliability Metrics

### Error Recovery Rate

| Scenario | Expected Behavior | Target | How to Measure | Stage |
|----------|-------------------|--------|---------------|-------|
| API timeout | Retry once after 5s, then show clear error; conversation preserved | 100% graceful handling | Inject timeout in client mock; verify no crash + conversation intact | Stage 1 |
| API rate limit (429) | Back off exponentially (1s, 2s, 4s), max 3 retries, then inform user | 100% graceful handling | Mock 429 responses; verify backoff timing and user message | Stage 1 |
| Invalid API key | Single-line error with fix instructions; no retry loop | 100% graceful handling | Test with bad key in CI | Stage 1 |
| Malformed tool call | Log warning, send error result to model so it can self-correct | > 90% self-correction rate | Inject malformed JSON in tool call args; verify model retries correctly | Stage 2 |
| Tool execution failure | Return error message to model; model should adapt or inform user | > 80% model adaptation | Simulate file-not-found, permission denied; verify model response | Stage 2 |
| OCR on corrupt file | Return clear error message; do not crash | 100% graceful handling | Test with truncated PDF | Stage 3 |
| Network loss mid-stream | Detect disconnect, show partial response + error, preserve conversation | 100% graceful handling | Simulate connection drop in client | Stage 2 |
| Invalid skill YAML | Show specific validation error (line number, field name); do not load skill | 100% clear error reporting | Test with 5+ invalid YAML variants | Stage 4 |
| Ctrl+C during tool execution | Cancel tool, preserve conversation, return to prompt | 100% clean interrupt | Manual test + automated signal test | Stage 2 |

### Graceful Degradation Scenarios

| Scenario | Degraded Behavior | Stage |
|----------|-------------------|-------|
| No internet connection | Offline error on first API call; previously loaded skills still listed (metadata only) | Stage 2 |
| OCR endpoint unavailable | OCR tool returns error; agent falls back to informing user; other tools still work | Stage 3 |
| openpyxl not installed | file_write falls back to CSV for tabular data; warns user about missing optional dep | Stage 2 |
| python-docx not installed | file_write falls back to Markdown for document output; warns user | Stage 2 |
| Config file corrupted | Re-run config wizard with clear message about what happened; back up old file | Stage 1 |
| Skill YAML has unknown fields | Ignore unknown fields with warning; load skill with known fields | Stage 4 |

---

## 4. User Adoption Metrics

These are measured via optional, opt-in anonymous telemetry (disabled by default; enabled with `zhi config set telemetry true`). All metrics are aggregated, never individual.

| Metric | What to Measure | Target | How to Measure | Stage |
|--------|----------------|--------|---------------|-------|
| First-run success rate | % of installs that complete config wizard and get a valid API response | > 90% | Telemetry event: `first_run_complete` vs `first_run_started` | Stage 1 |
| Time to first response | Wall-clock time from `zhi` launch to first AI response displayed | < 60s (including config wizard) | Telemetry: timestamp delta between `repl_started` and `first_response` | Stage 2 |
| Time to first skill run | Wall-clock time from first launch to first `/run <skill>` | < 10 min for users who attempt it | Telemetry: timestamp delta between `first_run_complete` and `first_skill_run` | Stage 4 |
| Skill creation completion rate | % of `/skill new` starts that result in a saved, valid skill | > 70% | Telemetry: `skill_create_started` vs `skill_create_saved` | Stage 4 |
| Session length | Number of turns per session | Median > 5 turns | Telemetry: turn count per session | Stage 2 |
| Return rate | % of users who launch `zhi` on 3+ different days within first 2 weeks | > 40% | Telemetry: distinct session dates per install ID | Stage 5 |
| Skill reuse rate | Average number of `/run` invocations per created skill | > 3 runs per skill | Telemetry: run count per skill hash | Stage 4 |
| Error frustration rate | % of sessions that end within 30s of an error (user gave up) | < 15% | Telemetry: session end timestamp vs last error timestamp | Stage 5 |

---

## 5. Code Quality Metrics

### Test Coverage Targets

| Module | Minimum Line Coverage | Minimum Branch Coverage | Stage |
|--------|----------------------|------------------------|-------|
| `config.py` | 90% | 85% | Stage 1 |
| `client.py` | 85% | 80% | Stage 1 |
| `cli.py` | 80% | 75% | Stage 1 |
| `repl.py` | 80% | 75% | Stage 2 |
| `agent.py` | 90% | 85% | Stage 2 |
| `ui.py` | 70% | 60% | Stage 2 |
| `tools/base.py` | 95% | 90% | Stage 2 |
| `tools/file_read.py` | 90% | 85% | Stage 2 |
| `tools/file_write.py` | 90% | 85% | Stage 2 |
| `tools/file_list.py` | 90% | 85% | Stage 2 |
| `tools/ocr.py` | 85% | 80% | Stage 3 |
| `tools/shell.py` | 85% | 80% | Stage 3 |
| `tools/web_fetch.py` | 85% | 80% | Stage 3 |
| `tools/skill_create.py` | 85% | 80% | Stage 4 |
| `skills/loader.py` | 95% | 90% | Stage 4 |
| `skills/__init__.py` | 90% | 85% | Stage 4 |
| **Overall project** | **85%** | **80%** | Stage 5 |

### Linting Rules

| Rule | Tool | Configuration | Stage |
|------|------|--------------|-------|
| Code formatting | `ruff format` | Default settings (line length 88) | Stage 1 |
| Import sorting | `ruff` (isort rules) | `known-first-party = ["zhi"]` | Stage 1 |
| Linting | `ruff check` | `select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "RUF"]` | Stage 1 |
| No unused imports | `ruff` F401 | Error (not warning) | Stage 1 |
| No bare except | `ruff` E722 | Error | Stage 1 |
| Docstrings on public API | `ruff` D1xx | Warning for `tools/`, `skills/` modules | Stage 5 |

### Type Coverage

| Metric | Target | Tool | Stage |
|--------|--------|------|-------|
| Type annotation coverage | > 90% of public functions | `mypy --strict` or `pyright` | Stage 2 |
| No `Any` in public APIs | 0 occurrences | `mypy` + grep | Stage 2 |
| Type errors | 0 in CI | `mypy` in GitHub Actions | Stage 1 |
| `tools/base.py` (BaseTool ABC) | 100% typed | `mypy --strict` | Stage 2 |
| Skill YAML schema | Validated with typed dataclass or Pydantic model | Runtime validation | Stage 4 |

---

## 6. Cost Metrics

### API Cost Per Typical Session

| Session Type | Model | Estimated Tokens | Estimated Cost (USD) | How to Measure | Stage |
|-------------|-------|-----------------|---------------------|---------------|-------|
| Quick chat (5 turns, no tools) | GLM-5 | ~3,000 input + 1,500 output | ~$0.02-0.05 (¥0.14-0.36) | Log token counts from API response `usage` field | Stage 2 |
| Complex task (10 turns, 3 tool calls) | GLM-5 | ~8,000 input + 3,000 output | ~$0.08-0.15 (¥0.58-1.08) | Same | Stage 2 |
| Skill execution (simple) | GLM-4-flash | ~2,000 input + 500 output | ~$0.001-0.003 (¥0.007-0.022) | Same | Stage 4 |
| Skill execution (OCR + write) | GLM-4-flash + OCR API | ~4,000 input + 1,000 output + OCR call | ~$0.005-0.01 (¥0.036-0.072) | Same + OCR endpoint billing | Stage 4 |
| Skill creation (interactive) | GLM-5 | ~5,000 input + 2,000 output | ~$0.05-0.10 (¥0.36-0.72) | Same | Stage 4 |

### Cost Tracking Implementation

| Feature | Description | Stage |
|---------|------------|-------|
| Per-session token counter | Display total tokens used at `/exit` or on demand | Stage 2 |
| Per-session cost estimate | Estimate cost based on model pricing; display at session end | Stage 2 |
| Skill execution cost log | Track cost per `/run` invocation; display after completion | Stage 4 |
| Cost comparison display | When user switches models, show estimated cost difference | Stage 4 |

### Flash vs Smart Model Cost Comparison

| Task | GLM-5 Cost | GLM-4-flash Cost | Savings | Quality Trade-off |
|------|-----------|-----------------|---------|-------------------|
| Run `summarize` skill | ~$0.03 (¥0.22) | ~$0.002 (¥0.014) | ~93% | Acceptable for structured tasks |
| Run `compare-docs` skill | ~$0.08 (¥0.58) | ~$0.005 (¥0.036) | ~94% | Acceptable when skill prompt is well-crafted |
| Open-ended reasoning | ~$0.05 (¥0.36) | ~$0.003 (¥0.022) | ~94% | Noticeable quality drop; GLM-5 recommended |
| Skill creation | ~$0.08 (¥0.58) | N/A | N/A | GLM-5 required for reliable skill authoring |

**Target**: Skill execution on GLM-4-flash should cost < 10% of the equivalent GLM-5 execution, making daily use nearly free.

---

## 7. Cross-Platform Parity (macOS + Windows)

### Must Work Identically

| Feature | Specific Requirements | How to Verify | Stage |
|---------|----------------------|--------------|-------|
| Installation | `pip install zhi` succeeds on both platforms | CI matrix: macOS + Windows runners | Stage 1 |
| Config location | `~/.zhi/` on macOS, `%APPDATA%/zhi/` on Windows (via `platformdirs`) | Unit test with mocked platform | Stage 1 |
| Config wizard | Same prompts, same validation, same saved format | Integration test on both platforms | Stage 1 |
| REPL input | `prompt_toolkit` handles line editing, history, autocomplete on both | Manual test on both platforms | Stage 2 |
| All slash commands | Same parsing, same behavior, same output | Automated tests (platform-agnostic) | Stage 2 |
| file_write output path | `./zhi-output/` resolved correctly with `pathlib.Path` | Unit test with both path separators | Stage 2 |
| file_write all formats | `.xlsx`, `.docx`, `.csv`, `.json`, `.md`, `.txt` produce identical content | Byte-compare output files in CI on both platforms | Stage 2 |
| OCR tool | Same API call, same result parsing | API mock test (platform-independent) | Stage 3 |
| Shell tool | Executes via OS-native shell (`/bin/sh` on macOS, `cmd.exe` on Windows) | Integration test with simple commands on both | Stage 3 |
| Skill YAML loading | Same parsing, same validation | Automated tests | Stage 4 |
| Skill directory discovery | Finds skills in platform-appropriate user directory | Unit test with mocked `platformdirs` | Stage 4 |
| Ctrl+C interrupt | Clean interrupt and recovery on both platforms | Manual test; signal handling test | Stage 2 |
| Unicode output | CJK characters, emoji render correctly in terminal | Manual test with Chinese text on both platforms | Stage 2 |
| PyPI install | `pip install zhi` from PyPI, `zhi` command available in PATH | CI job: fresh virtualenv install on both platforms | Stage 5 |

### Platform-Specific Acceptable Differences

| Feature | macOS Behavior | Windows Behavior | Why |
|---------|---------------|-----------------|-----|
| Shell commands | Uses `/bin/sh` | Uses `cmd.exe` or PowerShell | OS-native shell semantics differ |
| Path display | `/Users/name/zhi-output/` | `C:\Users\name\zhi-output\` | OS convention |
| Terminal colors | Full 256-color via Rich | May degrade to 16-color on older terminals | Windows terminal compatibility varies |
| Config file path | `~/.zhi/config.yaml` | `C:\Users\name\AppData\Roaming\zhi\config.yaml` | `platformdirs` convention |

---

## Summary: Key Targets at a Glance

| Category | Primary KPI | Target |
|----------|------------|--------|
| Performance | REPL startup | < 500ms cold |
| Performance | Streaming first token | < 800ms |
| Reliability | Graceful error handling | 100% (no unhandled crashes) |
| Adoption | First-run success | > 90% |
| Adoption | Skill creation completion | > 70% |
| Quality | Test coverage (overall) | > 85% line, > 80% branch |
| Quality | Type coverage (public API) | > 90% |
| Cost | Skill execution vs interactive | < 10% relative cost |
| Cross-platform | Feature parity | 100% for core features |
