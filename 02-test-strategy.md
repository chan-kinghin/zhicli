# Test Strategy: `zhi` CLI

## Overview

This document defines a comprehensive test strategy for the `zhi` CLI project. Tests are organized by type (unit, integration, E2E), mapped to implementation stages, and designed for cross-platform reliability.

**Test framework**: `pytest` with `pytest-asyncio`, `pytest-mock`, `tmp_path (built-in pytest fixture)`
**Coverage target**: 90%+ for core modules (agent, tools, skills, config), 80%+ overall
**Conventions**: tests mirror `src/zhi/` structure under `tests/`

```
tests/
├── conftest.py              # Shared fixtures (mock client, tmp dirs, sample skills)
├── unit/
│   ├── test_config.py
│   ├── test_client.py
│   ├── test_agent.py
│   ├── test_repl.py
│   ├── test_ui.py
│   ├── tools/
│   │   ├── test_base.py
│   │   ├── test_file_read.py
│   │   ├── test_file_write.py
│   │   ├── test_file_list.py
│   │   ├── test_ocr.py
│   │   ├── test_shell.py
│   │   ├── test_web_fetch.py
│   │   └── test_skill_create.py
│   └── skills/
│       ├── test_loader.py
│       └── test_discovery.py
├── integration/
│   ├── test_agent_tools.py
│   ├── test_skill_execution.py
│   ├── test_repl_agent.py
│   └── test_config_wizard.py
├── e2e/
│   ├── test_first_run.py
│   ├── test_interactive_session.py
│   └── test_skill_workflow.py
└── fixtures/
    ├── skills/
    │   ├── valid_skill.yaml
    │   ├── minimal_skill.yaml
    │   ├── malformed_skill.yaml
    │   ├── missing_fields.yaml
    │   └── extra_fields.yaml
    ├── files/
    │   ├── sample.txt
    │   ├── sample.pdf
    │   └── sample.csv
    └── api_responses/
        ├── chat_completion.json
        ├── chat_with_tool_calls.json
        ├── ocr_response.json
        └── error_responses/
            ├── invalid_key.json
            ├── rate_limit.json
            └── server_error.json
```

---

## 1. Unit Tests

### 1.1 config.py (Stage 1)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_load_config_from_yaml` | Loads a valid config YAML file | Write a config YAML to tmp `~/.zhi/config.yaml` | Returns `Config` object with correct api_key, model, etc. |
| `test_load_config_env_var_override` | Env var `ZHI_API_KEY` overrides YAML value | Set env var + write YAML with different key | `config.api_key` matches env var, not YAML |
| `test_load_config_env_var_only` | Config works with env var and no YAML file | Set env var, no config file | Returns `Config` with api_key from env |
| `test_load_config_missing_all` | No YAML and no env var triggers wizard | No config file, no env var | Raises `ConfigNotFound` or returns sentinel indicating first-run |
| `test_save_config` | Saves config to YAML | Create `Config` object | File written at expected path with correct contents |
| `test_config_dir_platform` | Config dir uses `platformdirs` | Mock `platformdirs.user_config_dir` | Path matches platform expectation |
| `test_config_yaml_parse_error` | Handles corrupted YAML gracefully | Write invalid YAML to config path | Raises `ConfigError` with descriptive message |
| `test_config_partial_yaml` | Missing optional fields get defaults | YAML with only `api_key` | `model` defaults to `"glm-5"`, other fields have defaults |
| `test_config_wizard_saves` | First-run wizard writes config | Mock `input()` to provide api_key | Config file created with provided values |
| `test_config_permissions_error` | Handles unwritable config dir | Mock `open()` to raise `PermissionError` | Raises `ConfigError` with clear message about permissions |

### 1.2 client.py (Stage 1)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_chat_completion_basic` | Sends chat request and parses response | Mock Zhipu SDK `client.chat.completions.create` | Returns parsed message with `content` |
| `test_chat_completion_with_tools` | Sends tool definitions, gets tool_calls back | Mock SDK to return tool_calls response | Returns message with `tool_calls` list |
| `test_chat_completion_streaming` | Handles streaming responses | Mock SDK streaming iterator | Yields chunks, final message assembled correctly |
| `test_chat_invalid_api_key` | 401 response from API | Mock SDK to raise `AuthenticationError` | Raises `ZhiClientError` with "invalid API key" message |
| `test_chat_rate_limit` | 429 response from API | Mock SDK to raise `RateLimitError` | Raises `ZhiClientError` with rate limit message |
| `test_chat_server_error` | 500 response from API | Mock SDK to raise `APIError` | Raises `ZhiClientError` with retry suggestion |
| `test_chat_network_timeout` | Connection timeout | Mock SDK to raise `Timeout` or `ConnectionError` | Raises `ZhiClientError` with network error message |
| `test_chat_model_selection` | Correct model parameter passed | Mock SDK, call with `model="glm-4-flash"` | SDK called with `model="glm-4-flash"` |
| `test_chat_thinking_mode` | Thinking mode parameter set correctly | Mock SDK, call with `thinking=True` | SDK called with thinking/reasoning param enabled |
| `test_ocr_endpoint` | Calls OCR layout parsing API | Mock HTTP POST to `/v4/layout_parsing` | Returns extracted markdown text |
| `test_ocr_invalid_file` | OCR with non-existent file | Call with path to missing file | Raises descriptive error |
| `test_ocr_large_file` | OCR with file exceeding size limit | Mock file size check | Raises error with size limit info |

### 1.3 agent.py (Stage 2)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_agent_single_turn_text` | Model responds with text only (no tools) | Mock client returns text message | Returns text content, no tool execution |
| `test_agent_single_tool_call` | Model requests one tool call | Mock client returns 1 tool_call, then text | Tool executed, result appended, final text returned |
| `test_agent_multi_tool_calls` | Model requests multiple tool calls in one turn | Mock client returns 3 tool_calls | All 3 tools executed, results appended |
| `test_agent_multi_turn_loop` | Model does tool call, gets result, does another | Mock client returns tool_call, then another tool_call, then text | Both tools executed across 2 turns |
| `test_agent_max_turns_limit` | Agent stops after max_turns | Mock client to always return tool_calls | Loop exits after `max_turns` iterations |
| `test_agent_permission_approve` | Risky tool approved by user | Mock permission callback returns `True` | Tool executed normally |
| `test_agent_permission_deny` | Risky tool denied by user | Mock permission callback returns `False` | Tool skipped, denied message sent to model |
| `test_agent_safe_tool_no_prompt` | Safe tool runs without permission check | Mock safe tool | Tool executed, permission callback not called |
| `test_agent_unknown_tool` | Model requests tool not in registry | Mock client returns unknown tool name | Error message sent back to model, agent continues |
| `test_agent_tool_execution_error` | Tool raises exception during execution | Mock tool.execute to raise | Error message sent back to model with traceback info |
| `test_agent_empty_response` | Model returns empty content and no tool_calls | Mock client returns empty | Agent handles gracefully, returns empty or prompts |
| `test_agent_message_history` | Messages accumulate correctly | Run multi-turn | `messages` list contains system, user, assistant, tool_result in order |
| `test_agent_auto_mode` | Auto mode skips all permission checks | Set mode to auto | All risky tools execute without callback |
| `test_agent_interrupt_mid_loop` | Simulated interrupt preserves state | Raise `KeyboardInterrupt` after first tool_call | Messages up to interruption point are preserved |

### 1.4 tools/ (Stage 2-3)

#### tools/base.py

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_base_tool_schema_generation` | BaseTool generates correct JSON schema | Subclass with typed params | `to_schema()` returns valid OpenAI-compatible function schema |
| `test_base_tool_risky_flag` | Risky flag defaults and overrides | Subclass with/without `risky = True` | Default is `False`; override works |
| `test_tool_registry_register` | Tool registered by name | Register a tool | `registry["tool_name"]` returns the tool |
| `test_tool_registry_duplicate` | Duplicate registration raises error | Register same name twice | Raises `ValueError` |
| `test_tool_registry_list` | Lists all registered tools | Register 3 tools | `registry.list()` returns 3 tool schemas |
| `test_tool_registry_filter_by_names` | Filter registry to subset | Register 5 tools, filter to 2 names | Returns only the 2 named tools |

#### tools/file_read.py

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_file_read_text` | Reads a text file | Create tmp file with content | Returns file content as string |
| `test_file_read_nonexistent` | File does not exist | Path to missing file | Returns error message (not exception) |
| `test_file_read_binary` | Attempts to read binary file | Create tmp binary file | Returns error or base64-encoded content |
| `test_file_read_large` | File exceeds size limit | Create large tmp file | Returns truncated content with warning |
| `test_file_read_permission_denied` | No read permission | Create file, `chmod 000` | Returns permission error message |
| `test_file_read_encoding` | Handles non-UTF8 encoding | Create file with latin-1 content | Handles gracefully or reports encoding issue |

#### tools/file_write.py

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_file_write_text` | Writes plain text file | Provide content + `.txt` path | File created in `zhi-output/` with correct content |
| `test_file_write_markdown` | Writes markdown file | Provide content + `.md` path | File created with markdown content |
| `test_file_write_json` | Writes formatted JSON | Provide dict + `.json` path | File contains pretty-printed JSON |
| `test_file_write_csv` | Writes CSV from structured data | Provide rows + `.csv` path | Valid CSV file created |
| `test_file_write_xlsx` | Writes Excel spreadsheet | Provide tabular data + `.xlsx` path | Valid Excel file readable by openpyxl |
| `test_file_write_docx` | Writes Word document | Provide text + `.docx` path | Valid docx readable by python-docx |
| `test_file_write_output_dir` | Defaults to `zhi-output/` | No explicit dir | File path starts with `./zhi-output/` |
| `test_file_write_creates_dir` | Creates output dir if missing | Remove `zhi-output/` | Directory created automatically |
| `test_file_write_no_overwrite` | Refuses to overwrite existing file | Create file first, then write same path | Returns error about existing file |
| `test_file_write_risky_flag` | Tool is marked risky | Inspect tool | `risky == True` |
| `test_file_write_disk_full` | Handles disk full error | Mock `open()` to raise `OSError(errno.ENOSPC)` | Returns descriptive disk full message |
| `test_file_write_path_traversal` | Rejects `../` in paths | Path with `../../etc/passwd` | Rejects with security error |

#### File Write Safety Tests

| Test | Setup | Action | Expected |
|------|-------|--------|----------|
| `test_file_write_symlink_attack_blocked` | Symlink in `zhi-output/` pointing to `/etc/passwd` | Write to symlink name | Refused — resolved path is outside output directory |
| `test_file_write_auto_mode_overwrite_confirms` | Auto mode, existing file in `zhi-output/` | Write same filename | Still prompts for overwrite confirmation — auto mode does NOT bypass |

#### tools/file_list.py

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_file_list_directory` | Lists directory contents | Create tmp dir with files | Returns list of filenames |
| `test_file_list_empty` | Lists empty directory | Create empty tmp dir | Returns empty list or message |
| `test_file_list_nonexistent` | Directory does not exist | Path to missing dir | Returns error message |
| `test_file_list_nested` | Shows files recursively or flat | Create nested structure | Returns expected listing format |

#### tools/ocr.py (Stage 3)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_ocr_pdf` | OCR a PDF file | Mock OCR API response | Returns extracted markdown text |
| `test_ocr_image` | OCR an image file | Mock OCR API response | Returns extracted text |
| `test_ocr_unsupported_format` | Non-image/PDF file | Call with `.py` file | Returns error about unsupported format |
| `test_ocr_api_failure` | OCR API returns error | Mock API to raise | Returns descriptive error |
| `test_ocr_empty_result` | OCR returns no text | Mock API returns empty | Returns message about no text found |

#### tools/shell.py (Stage 3)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_shell_simple_command` | Runs `echo hello` | None | Returns stdout `"hello"` |
| `test_shell_exit_code` | Reports non-zero exit code | Command that fails | Returns stderr + exit code |
| `test_shell_timeout` | Command exceeds timeout | `sleep 999` with 1s timeout | Returns timeout error |
| `test_shell_risky_flag` | Tool is marked risky | Inspect tool | `risky == True` |
| `test_shell_cross_platform` | Uses correct shell per OS | Mock `sys.platform` | Uses `cmd.exe` on Windows, `/bin/sh` on Unix |
| `test_shell_output_limit` | Truncates extremely long output | Command producing >100KB | Output truncated with warning |

#### Shell Safety Tests (File Safety Guarantee)

| Test | Setup | Action | Expected |
|------|-------|--------|----------|
| `test_shell_always_requires_confirmation` | Auto mode enabled | Shell tool invoked | Still prompts for confirmation — auto mode does NOT apply to shell |
| `test_shell_process_group_kill` | Command that spawns child processes | Timeout reached | Entire process group killed, no orphan processes |
| `test_shell_destructive_command_warning` | Command containing `rm`, `del`, or `mv` | Shell tool processes command | Extra-prominent warning displayed before confirmation prompt |
| `test_shell_command_blocklist` | Command matching blocklist (`rm -rf /`, `mkfs`, fork bomb) | Shell tool processes command | Command rejected outright with error returned to model |

#### tools/web_fetch.py (Stage 3)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_web_fetch_success` | Fetches URL content | Mock httpx GET 200 | Returns page text |
| `test_web_fetch_404` | URL returns 404 | Mock httpx GET 404 | Returns error message |
| `test_web_fetch_timeout` | Connection timeout | Mock httpx to raise `TimeoutException` | Returns timeout error |
| `test_web_fetch_invalid_url` | Malformed URL | Pass `"not-a-url"` | Returns validation error |

#### tools/skill_create.py (Stage 4)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_skill_create_valid` | Creates a valid skill YAML | Provide complete skill data | YAML file written to `~/.zhi/skills/` |
| `test_skill_create_validates_tools` | Only known tools allowed | Include `"delete_all"` in tools list | Rejects with unknown tool error |
| `test_skill_create_risky_flag` | Tool is marked risky | Inspect tool | `risky == True` |
| `test_skill_create_duplicate_name` | Skill name already exists | Create skill, then create same name | Asks for overwrite or rejects |

#### Skill Name Safety Tests

| Test | Setup | Action | Expected |
|------|-------|--------|----------|
| `test_skill_name_path_traversal_rejected` | Skill name: `../../.bashrc` | Create or delete skill | Rejected with "Invalid skill name" error |
| `test_skill_name_special_chars_rejected` | Skill name: `my skill!@#` | Create skill | Rejected — only `[a-zA-Z0-9_-]` allowed |

### 1.5 skills/ (Stage 4)

#### skills/loader.py

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_load_valid_skill` | Parses a well-formed YAML skill | Load `fixtures/skills/valid_skill.yaml` | Returns `Skill` object with all fields |
| `test_load_minimal_skill` | Parses skill with only required fields | Load `fixtures/skills/minimal_skill.yaml` | Returns `Skill` with defaults for optional fields |
| `test_load_malformed_yaml` | Invalid YAML syntax | Load `fixtures/skills/malformed_skill.yaml` | Raises `SkillLoadError` with parse error details |
| `test_load_missing_required_fields` | YAML valid but missing `name` | Load `fixtures/skills/missing_fields.yaml` | Raises `SkillLoadError` listing missing fields |
| `test_load_unknown_tool_reference` | Skill references tool that does not exist | YAML with `tools: [nonexistent]` | Raises `SkillLoadError` about unknown tool |
| `test_load_extra_fields_ignored` | Extra YAML fields are silently ignored | Load `fixtures/skills/extra_fields.yaml` | Returns `Skill`, extra fields not present |
| `test_load_empty_file` | YAML file is empty | Load empty file | Raises `SkillLoadError` |
| `test_load_not_yaml_extension` | File is `.txt` not `.yaml` | Load `.txt` file | Raises error or loads based on content |
| `test_skill_model_default` | Model defaults to `glm-4-flash` | YAML with no `model` field | `skill.model == "glm-4-flash"` |
| `test_skill_max_turns_default` | Max turns defaults to 15 | YAML with no `max_turns` | `skill.max_turns == 15` |

#### skills/__init__.py (discovery)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_discover_builtin_skills` | Finds skills in `builtin/` directory | Default package state | Returns at least `summarize` and `translate` |
| `test_discover_user_skills` | Finds skills in `~/.zhi/skills/` | Create YAML in user skills dir | Returns user skill in listing |
| `test_discover_merge` | Builtin + user skills combined | Both dirs populated | Returns all skills, user can override builtin |
| `test_discover_empty_user_dir` | User skills dir missing or empty | No user skills dir | Returns only builtin skills, no error |
| `test_discover_corrupted_skill_skipped` | Bad YAML in user dir does not crash | Put malformed YAML in user dir | Skipped with warning, other skills still loaded |

### 1.6 repl.py (Stage 2)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_repl_help_command` | `/help` prints available commands | Mock input → `/help` | Output contains all slash commands |
| `test_repl_exit_command` | `/exit` terminates REPL | Mock input → `/exit` | Loop exits cleanly |
| `test_repl_auto_mode` | `/auto` switches to auto mode | Mock input → `/auto` | Agent permission mode set to auto |
| `test_repl_approve_mode` | `/approve` switches to approve mode | Mock input → `/approve` | Agent permission mode set to approve |
| `test_repl_model_switch` | `/model glm-4-flash` changes model | Mock input → `/model glm-4-flash` | Client model updated |
| `test_repl_model_invalid` | `/model nonexistent` shows error | Mock input → `/model xyz` | Prints error with valid model list |
| `test_repl_think_command` | `/think` enables thinking mode | Mock input → `/think` | Thinking mode flag set to True |
| `test_repl_fast_command` | `/fast` disables thinking mode | Mock input → `/fast` | Thinking mode flag set to False |
| `test_repl_unknown_command` | `/blah` shows error | Mock input → `/blah` | Prints "unknown command" message |
| `test_repl_regular_text` | Non-slash input routed to agent | Mock input → `"hello"` | `agent.run` called with `"hello"` |
| `test_repl_run_command` | `/run skill_name arg1` invokes skill | Mock input → `/run summarize file.txt` | Skill executed with args |
| `test_repl_skill_list` | `/skill list` shows skills | Mock input → `/skill list` | Prints skill names and descriptions |
| `test_repl_skill_new` | `/skill new` starts creation flow | Mock input → `/skill new` | Enters interactive skill creation |
| `test_repl_keyboard_interrupt` | Ctrl+C mid-response returns to prompt | Raise `KeyboardInterrupt` during agent.run | Prints interruption message, returns to prompt |
| `test_repl_empty_input` | Empty input ignored | Mock input → `""` | Prompt shown again, no agent call |

### 1.7 ui.py (Stage 2)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_ui_stream_text` | Streams text character by character | Call `ui.stream("hello")` | Output matches `"hello"` |
| `test_ui_permission_prompt_yes` | Permission prompt returns True on "y" | Mock input → `"y"` | Returns `True` |
| `test_ui_permission_prompt_no` | Permission prompt returns False on "n" | Mock input → `"n"` | Returns `False` |
| `test_ui_thinking_display` | Thinking block rendered dimmed | Call `ui.show_thinking("reasoning")` | Output contains thinking content |
| `test_ui_tool_status` | Tool execution status displayed | Call `ui.show_tool("file_write", "output.txt")` | Prints tool icon + name + arg |

---

## 2. Integration Tests

### 2.1 Agent + Tools (Stage 2)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_agent_file_read_write_flow` | Agent reads a file, then writes transformed content | Mock client to: 1) call file_read, 2) call file_write. Create source file in tmp dir | Source file read, transformed file written to `zhi-output/` |
| `test_agent_multi_tool_chain` | Agent chains file_list -> file_read -> file_write | Mock client for 3 sequential tool calls | Each tool gets correct input from prior tool's output |
| `test_agent_permission_deny_continues` | Deny file_write, agent adapts | Mock: 1) tool_call file_write (denied), 2) text response | Agent sends denial to model, model responds with text |
| `test_agent_tool_error_recovery` | Tool fails, agent retries differently | Mock: 1) file_read fails, 2) model requests different path, 3) success | Agent recovers from tool error |
| `test_agent_auto_mode_full_chain` | Auto mode executes all tools without prompts | Mock client for 3 risky tool calls, auto mode | All tools execute, no permission callbacks |

### 2.2 Skill Loading + Execution (Stage 4)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_skill_load_and_run` | Load YAML skill, execute with agent | Valid skill YAML + mock client | Agent runs with skill's system prompt, model, and tool subset |
| `test_skill_tool_restriction` | Skill cannot use unlisted tools | Skill lists only `file_read`; mock client requests `shell` | `shell` tool call rejected or not in registry |
| `test_skill_model_override` | Skill uses its own model, not session model | Skill with `model: glm-4-flash`, session on `glm-5` | Client called with `glm-4-flash` |
| `test_skill_args_passed` | Skill receives file arguments | `/run compare-docs file1.txt file2.txt` | Files passed as context in messages |
| `test_skill_max_turns_enforced` | Skill stops at max_turns | Skill with `max_turns: 3`, mock client to loop | Agent stops after 3 turns |
| `test_skill_thinking_off_by_default` | Skill execution has thinking disabled | Run skill | Client called with thinking disabled |

### 2.3 REPL + Agent (Stage 2)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_repl_sends_to_agent` | User text message processed by agent | Mock input → text, mock agent | `agent.run` called with user text |
| `test_repl_slash_not_to_agent` | Slash commands handled locally | Mock input → `/help` | `agent.run` NOT called |
| `test_repl_mode_affects_agent` | `/auto` changes agent behavior | `/auto` then text message | Agent runs with auto permission mode |
| `test_repl_model_affects_agent` | `/model` changes agent model | `/model glm-4-flash` then text | Agent uses `glm-4-flash` |
| `test_repl_conversation_persists` | Multiple messages share history | Send 3 messages | Agent's message list grows across turns |
| `test_repl_interrupt_preserves_history` | Ctrl+C keeps partial results | Interrupt mid-agent, send new message | New agent call has prior context |

### 2.4 Config Wizard (Stage 1)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_wizard_first_run_flow` | No config triggers wizard, saves result | No config file, mock inputs | Config file created, REPL starts |
| `test_wizard_invalid_key_retry` | Invalid key format prompts retry | Mock first input invalid, second valid | Second key saved |

---

## 3. End-to-End Tests

These tests simulate full user sessions. They use mock API responses but exercise the full code path from CLI entry to output.

### 3.1 First Run (Stage 1)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_e2e_first_run_wizard` | Fresh install → config wizard → REPL | No config, mock inputs for key + `/exit` | Config created, REPL launched, exited cleanly |

### 3.2 Interactive Session (Stage 2-3)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_e2e_simple_question` | User asks a question, gets text answer | Config present, mock client text response | Response printed, returns to prompt |
| `test_e2e_file_write_approve` | User triggers file write, approves | Mock client → file_write tool call, mock input `"y"` | File written to `zhi-output/`, success message |
| `test_e2e_file_write_deny` | User triggers file write, denies | Mock client → file_write tool call, mock input `"n"` | No file written, model informed of denial |
| `test_e2e_auto_mode_session` | Switch to auto, multiple tool calls | `/auto`, then prompt, mock multi-tool response | All tools execute without prompts |
| `test_e2e_ocr_to_excel` | OCR a file, write as Excel | Mock OCR + file_write tool calls | `.xlsx` file created with OCR content |
| `test_e2e_interrupt_and_continue` | Ctrl+C mid-task, then new instruction | Interrupt during tool execution | Partial state preserved, new instruction uses context |

### 3.3 Skill Workflow (Stage 4)

| Test Name | Description | Setup | Expected Behavior |
|-----------|-------------|-------|-------------------|
| `test_e2e_create_and_run_skill` | Create skill in conversation, then `/run` it | Mock skill creation flow, then mock skill execution | Skill YAML saved, `/run` executes with cheap model |
| `test_e2e_skill_list` | `/skill list` shows builtin + user skills | Builtin skills + 1 user skill | All skills listed with names and descriptions |
| `test_e2e_run_builtin_skill` | `/run summarize file.txt` | Builtin summarize skill + mock client | Summarization generated using skill model |
| `test_e2e_skill_with_args` | `/run compare-docs a.txt b.txt` | User skill + two tmp files | Both files processed, output generated |

---

## 4. Edge Cases

### 4.1 API Failures

| Test Name | Description | Setup | Expected Behavior | Stage |
|-----------|-------------|-------|-------------------|-------|
| `test_edge_invalid_api_key` | 401 from API on first request | Mock 401 response | Clear error: "Invalid API key. Check ZHI_API_KEY or ~/.zhi/config.yaml" | 1 |
| `test_edge_rate_limit` | 429 from API | Mock 429 response | Error with suggestion to wait or use cheaper model | 1 |
| `test_edge_server_error_500` | 500 from API | Mock 500 response | Error: "Zhipu API server error. Try again later." | 1 |
| `test_edge_network_timeout` | Connection timeout | Mock `ConnectionError` | Error: "Cannot reach Zhipu API. Check your internet connection." | 1 |
| `test_edge_malformed_api_response` | API returns unexpected JSON shape | Mock response missing `choices` | Handled gracefully with descriptive error | 1 |
| `test_edge_empty_tool_calls` | API returns empty tool_calls list | Mock `tool_calls: []` | Treated as text-only response | 2 |
| `test_edge_api_mid_stream_failure` | Stream dies mid-response | Mock streaming that errors after 3 chunks | Partial response shown, error reported | 2 |

### 4.2 Malformed Skills

| Test Name | Description | Setup | Expected Behavior | Stage |
|-----------|-------------|-------|-------------------|-------|
| `test_edge_skill_invalid_yaml_syntax` | YAML with tab indentation errors | Malformed YAML file | `SkillLoadError` with line number | 4 |
| `test_edge_skill_missing_name` | YAML missing required `name` field | YAML without `name` | `SkillLoadError`: "missing required field: name" | 4 |
| `test_edge_skill_empty_tools` | `tools: []` — no tools available | Valid YAML with empty tools | Skill loads but agent can only produce text | 4 |
| `test_edge_skill_nonexistent_tool` | `tools: [laser_cannon]` | YAML referencing unknown tool | `SkillLoadError`: "unknown tool: laser_cannon" | 4 |
| `test_edge_skill_binary_file` | Try loading a PNG as skill | PNG file in skills dir | Skipped with warning | 4 |
| `test_edge_skill_unicode_name` | Skill named with CJK characters | `name: "文档比较"` | Loads and runs correctly | 4 |
| `test_edge_skill_circular_max_turns_zero` | `max_turns: 0` | YAML with 0 max turns | Error or immediate return | 4 |

### 4.3 File System Errors

| Test Name | Description | Setup | Expected Behavior | Stage |
|-----------|-------------|-------|-------------------|-------|
| `test_edge_disk_full_on_write` | Write fails with ENOSPC | Mock `open()` → `OSError(errno.ENOSPC)` | "Disk full" error returned to model | 2 |
| `test_edge_permission_denied_write` | Cannot write to output dir | Mock `open()` → `PermissionError` | "Permission denied" error with path info | 2 |
| `test_edge_permission_denied_read` | Cannot read requested file | `chmod 000` on tmp file | "Permission denied" error | 2 |
| `test_edge_path_too_long` | Filename exceeds OS limit | 500-char filename | OS error caught and reported | 2 |
| `test_edge_special_chars_in_path` | Spaces and unicode in file path | File with spaces and accents | Handled correctly via `pathlib.Path` | 2 |
| `test_edge_symlink_read` | Reading a symlink target | Create symlink to real file | Reads the target file content | 2 |
| `test_edge_output_dir_is_file` | `zhi-output` exists as a file, not dir | Create file named `zhi-output` | Error: "zhi-output exists but is not a directory" | 2 |

### 4.4 REPL Edge Cases

| Test Name | Description | Setup | Expected Behavior | Stage |
|-----------|-------------|-------|-------------------|-------|
| `test_edge_eof_input` | User sends EOF (Ctrl+D) | Mock `EOFError` from `prompt()` | REPL exits gracefully | 2 |
| `test_edge_very_long_input` | User pastes 100KB of text | Mock 100KB input string | Sent to agent (may be truncated by API) | 2 |
| `test_edge_slash_only` | User types just `/` | Mock input → `"/"` | Shows "unknown command" or help | 2 |
| `test_edge_slash_with_spaces` | `/run   summarize   file.txt` | Extra spaces in command | Parsed correctly after stripping | 2 |
| `test_edge_run_nonexistent_skill` | `/run ghost_skill` | No such skill exists | Error: "Skill 'ghost_skill' not found" | 4 |

---

## 5. Cross-Platform Considerations

### 5.1 Path Handling

| Test Name | Description | Platform Notes | Expected Behavior |
|-----------|-------------|----------------|-------------------|
| `test_xplat_config_dir_macos` | Config at `~/.zhi/` on macOS | `sys.platform == "darwin"` | `platformdirs` returns `~/.zhi/` equivalent |
| `test_xplat_config_dir_windows` | Config at `%APPDATA%/zhi` on Windows | `sys.platform == "win32"` | `platformdirs` returns AppData path |
| `test_xplat_path_separators` | Paths use OS-native separators | Create paths with `pathlib.Path` | Forward slashes on macOS, backslashes on Windows |
| `test_xplat_home_expansion` | `~` expands correctly | Use `Path.home()` | Correct home dir on both platforms |
| `test_xplat_output_dir` | `zhi-output/` created correctly | Both platforms | Directory created with correct path |

### 5.2 Shell Differences

| Test Name | Description | Platform Notes | Expected Behavior |
|-----------|-------------|----------------|-------------------|
| `test_xplat_shell_echo` | `echo hello` works on both | `/bin/sh` vs `cmd.exe` | Returns `"hello"` on both |
| `test_xplat_shell_selection` | Correct shell binary used | Check `sys.platform` | `cmd.exe` on Windows, `/bin/sh` on macOS/Linux |
| `test_xplat_shell_encoding` | Non-ASCII output from shell | Run command with unicode output | Decoded correctly on both platforms |

### 5.3 Implementation Approach

Cross-platform tests should use `pytest` parametrize with platform mocking where actual platform testing is not available:

```python
@pytest.fixture
def mock_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(platformdirs, "user_config_dir", lambda appname: f"C:\\Users\\Test\\AppData\\Roaming\\{appname}")

@pytest.fixture
def mock_macos(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platformdirs, "user_config_dir", lambda appname: f"/Users/test/.{appname}")
```

CI runs actual tests on both platforms (see section 7).

---

## 6. Mock Strategy

### 6.1 Zhipu API Mocking

The Zhipu SDK client is the primary external dependency. Mock at the SDK boundary:

```python
@pytest.fixture
def mock_zhipu_client(mocker):
    """Mock the Zhipu SDK client for all tests."""
    client = mocker.MagicMock()

    # Default: return a simple text response
    response = mocker.MagicMock()
    response.choices = [mocker.MagicMock()]
    response.choices[0].message.content = "Hello from GLM"
    response.choices[0].message.tool_calls = None
    client.chat.completions.create.return_value = response

    return client


def make_tool_call_response(mocker, tool_name, arguments, call_id="call_1"):
    """Helper to create a mock response with tool_calls."""
    response = mocker.MagicMock()
    tool_call = mocker.MagicMock()
    tool_call.id = call_id
    tool_call.function.name = tool_name
    tool_call.function.arguments = json.dumps(arguments)
    response.choices = [mocker.MagicMock()]
    response.choices[0].message.content = None
    response.choices[0].message.tool_calls = [tool_call]
    return response


def make_streaming_response(mocker, chunks):
    """Helper to create a mock streaming response."""
    for chunk in chunks:
        delta = mocker.MagicMock()
        delta.choices = [mocker.MagicMock()]
        delta.choices[0].delta.content = chunk
        yield delta
```

**Key principle**: Mock at the `client.chat.completions.create` level, not at HTTP level. This keeps tests independent of SDK internals.

For OCR, mock the HTTP client directly since it uses a REST endpoint:

```python
@pytest.fixture
def mock_ocr_api(mocker):
    """Mock the OCR layout parsing endpoint."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "Extracted OCR text..."}
    mocker.patch("httpx.post", return_value=mock_response)
    return mock_response
```

### 6.2 File System Mocking

Use `tmp_path` (built-in pytest fixture) for all file operations. Never touch real filesystem:

```python
@pytest.fixture
def workspace(tmp_path):
    """Set up a workspace with input files and output dir."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "zhi-output"
    # Don't create output_dir — let file_write create it

    # Sample files
    (input_dir / "sample.txt").write_text("Hello world")
    (input_dir / "data.csv").write_text("a,b,c\n1,2,3")

    return {"root": tmp_path, "input": input_dir, "output": output_dir}


@pytest.fixture
def mock_config_dir(tmp_path, monkeypatch):
    """Redirect config dir to tmp for isolation."""
    config_dir = tmp_path / ".zhi"
    config_dir.mkdir()
    monkeypatch.setattr("zhi.config.get_config_dir", lambda: config_dir)
    return config_dir
```

For error simulation:

```python
def test_disk_full(workspace, monkeypatch):
    original_open = builtins.open
    def mock_open(*args, **kwargs):
        if "zhi-output" in str(args[0]):
            raise OSError(errno.ENOSPC, "No space left on device")
        return original_open(*args, **kwargs)
    monkeypatch.setattr(builtins, "open", mock_open)
```

### 6.3 User Input Mocking

Mock `prompt_toolkit` input for REPL tests:

```python
@pytest.fixture
def mock_repl_input(mocker):
    """Provide scripted user inputs to the REPL."""
    def make_input(responses):
        it = iter(responses)
        def mock_prompt(*args, **kwargs):
            try:
                return next(it)
            except StopIteration:
                raise EOFError()
        mocker.patch("zhi.repl.prompt", side_effect=mock_prompt)
    return make_input
```

### 6.4 Mock Hierarchy

```
Level 1 (Unit):     Mock SDK client, filesystem via tmp_path, user input
Level 2 (Integ):    Mock SDK client only; real filesystem (tmp_path), real tool execution
Level 3 (E2E):      Mock SDK client only; everything else is real (tmp_path for isolation)
```

---

## 7. CI Pipeline Design

### 7.1 Every PR (fast, <3 minutes)

```yaml
name: CI
on: [pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff mypy
      - run: ruff check src/ tests/
      - run: ruff format --check src/ tests/
      - run: mypy src/zhi/ --strict

  test-unit:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -v --tb=short --cov=zhi --cov-report=xml
      - uses: codecov/codecov-action@v4

  test-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/integration/ -v --tb=short
```

**Triggers**: Every PR, every push to `main`.
**Time budget**: <3 minutes total.
**What's tested**: Linting, type checking, all unit tests on 3 Python versions, integration tests on one version.

### 7.2 Nightly (comprehensive, <15 minutes)

```yaml
name: Nightly
on:
  schedule:
    - cron: "0 4 * * *"   # 4 AM UTC daily
  workflow_dispatch:       # manual trigger

jobs:
  test-full:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.10", "3.11", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --tb=long --cov=zhi --cov-report=xml
      - uses: codecov/codecov-action@v4

  test-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/e2e/ -v --tb=long

  dependency-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pip-audit
      - run: pip-audit .
```

**What's added over PR**: Cross-platform matrix (macOS + Windows + Linux), all Python versions, E2E tests, dependency security audit.

### 7.3 Release (on tag push)

```yaml
name: Release
on:
  push:
    tags: ["v*"]

jobs:
  test-release:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v

  publish:
    needs: test-release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

### 7.4 Test Configuration

`pyproject.toml` test settings:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: Unit tests (fast, no external deps)",
    "integration: Integration tests (mock API only)",
    "e2e: End-to-end tests (full workflow)",
    "slow: Tests that take >5 seconds",
    "xplat: Cross-platform specific tests",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:prompt_toolkit.*",
]

[tool.coverage.run]
source = ["zhi"]
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.",
]
```

---

## 8. Test-to-Stage Mapping

| Stage | Unit Tests | Integration Tests | E2E Tests |
|-------|-----------|-------------------|-----------|
| **Stage 1**: Scaffold + Config + Client | config (10), client (12) | config wizard (2) | first run (1) |
| **Stage 2**: REPL + Tools + Agent | agent (14), repl (15), ui (5), base (6), file_read (6), file_write (12), file_list (4) | agent+tools (5), REPL+agent (6) | interactive session (6) |
| **Stage 3**: OCR + Shell + Web | ocr (5), shell (6), web_fetch (4) | - | OCR-to-Excel (1) |
| **Stage 4**: Skill System | loader (10), discovery (5), skill_create (4) | skill execution (6) | skill workflow (4) |
| **Stage 5**: Polish + Publish | - | - | Full workflow validation |

**Total test count**: ~148 tests

---

## 9. Dev Dependencies

Add to `pyproject.toml` under `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-mock>=3.12",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "mypy>=1.10",
]
```

---

## 10. Testing Principles

1. **Mock at boundaries, not internals**: Mock the Zhipu SDK and filesystem, not internal functions.
2. **Every tool test uses tmp_path**: No test writes to real filesystem.
3. **Fixture-based API responses**: Pre-recorded response JSONs in `tests/fixtures/` for deterministic results.
4. **Test names describe behavior**: `test_agent_permission_deny_continues` not `test_agent_3`.
5. **One assertion per test where practical**: Makes failures immediately clear.
6. **Fast by default**: Unit tests must complete in <10 seconds total. Integration in <30 seconds.
7. **No network calls in tests**: All external APIs mocked. Tests run offline.
8. **Cross-platform via parametrize**: Use monkeypatch to simulate Windows paths on macOS CI and vice versa.
