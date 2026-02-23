# Configuration Reference

## Config File

zhi stores its configuration in a YAML file at a platform-specific location:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/zhi/config.yaml` |
| Linux | `~/.config/zhi/config.yaml` |
| Windows | `%APPDATA%\zhi\config.yaml` |

The config file is created automatically by the setup wizard (`zhi --setup`) with permissions set to `0o600` (owner read/write only) to protect the API key.

---

## Config Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_key` | string | `""` | Zhipu API key (required for all operations) |
| `default_model` | string | `"glm-5"` | Default model for interactive chat |
| `skill_model` | string | `"glm-4-flash"` | Default model for skill execution |
| `output_dir` | string | `"zhi-output"` | Output directory for `file_write` tool |
| `max_turns` | int | `30` | Maximum agent loop turns per request (range: 1-100) |
| `log_level` | string | `"INFO"` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `language` | string | `"auto"` | UI language (`auto`, `en`, `zh`) |

### Example config.yaml

```yaml
api_key: "your-zhipu-api-key-here"
default_model: glm-5
skill_model: glm-4-flash
output_dir: zhi-output
max_turns: 30
log_level: INFO
language: auto
```

---

## Environment Variables

Environment variables override config file values. This is the priority order:

**Environment variables > Config file > Defaults**

| Variable | Maps to | Example |
|----------|---------|---------|
| `ZHI_API_KEY` | `api_key` | `export ZHI_API_KEY="your-key"` |
| `ZHI_DEFAULT_MODEL` | `default_model` | `export ZHI_DEFAULT_MODEL="glm-4-flash"` |
| `ZHI_OUTPUT_DIR` | `output_dir` | `export ZHI_OUTPUT_DIR="output"` |
| `ZHI_LOG_LEVEL` | `log_level` | `export ZHI_LOG_LEVEL="DEBUG"` |
| `ZHI_LANGUAGE` | `language` | `export ZHI_LANGUAGE="zh"` |
| `NO_COLOR` | (disables colors) | `export NO_COLOR=1` |

!!! tip "Quick start without config file"
    You can skip the setup wizard entirely by setting `ZHI_API_KEY`:
    ```bash
    export ZHI_API_KEY="your-key"
    zhi
    ```

---

## Language Detection

When `language` is set to `auto` (the default), zhi detects the UI language using:

1. `ZHI_LANGUAGE` environment variable
2. `LANG` or `LC_ALL` environment variables (checks for `zh` prefix)
3. Falls back to `en` (English)

!!! info "Language preamble"
    Regardless of UI language, all skill prompts include a language preamble that instructs the LLM to respond in the same language as the input document. This ensures that Chinese documents get Chinese responses and English documents get English responses.

---

## Setup Wizard

Run the setup wizard for first-time configuration or to reconfigure:

```bash
zhi --setup
```

The wizard walks through three steps:

### Step 1: API Key

Paste your Zhipu API key (obtain one at [open.bigmodel.cn](https://open.bigmodel.cn)).

### Step 2: Defaults

Configure optional settings:

| Setting | Prompt | Default |
|---------|--------|---------|
| Chat model | `Default model for chat [glm-5]:` | `glm-5` |
| Skill model | `Default model for skills [glm-4-flash]:` | `glm-4-flash` |
| Output directory | `Output directory [zhi-output]:` | `zhi-output` |
| Language | `Interface language [auto]:` | `auto` |

### Step 3: Quick Demo

Optional demo of a sample skill (press Enter or `y` to try, `n` to skip).

---

## Validation

On load, the config is validated:

| Check | Behavior |
|-------|----------|
| Missing API key | Warning logged, commands requiring API access will fail |
| `max_turns` out of range (1-100) | Clamped to valid range with warning |
| Unknown `log_level` | Reset to `INFO` with warning |
| Unknown config fields | Silently ignored |
| Malformed YAML | Falls back to defaults with warning |

---

## File Permissions

The config file is saved with `0o600` permissions (owner read/write only). If permissions cannot be set (e.g., on Windows), a warning is logged:

```
Could not set restrictive permissions on config.yaml. API key may be readable by other users.
```

!!! warning "Protect your API key"
    The config file contains your Zhipu API key in plain text. Ensure the file is not readable by other users. Using the `ZHI_API_KEY` environment variable is a safer alternative for shared systems.
