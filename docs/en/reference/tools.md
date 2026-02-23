# Tools Reference

zhi provides **7 built-in tools** that the agent can call during conversations and skill execution. Each tool has a risk level that determines whether user confirmation is required.

## Risk Levels

| Level | Behavior in `approve` mode | Behavior in `auto` mode |
|-------|---------------------------|------------------------|
| **Low** | No confirmation needed | No confirmation needed |
| **High** | Confirmation required | No confirmation needed |
| **Always** | Always requires confirmation | Always requires confirmation |

---

## file_read

Read the contents of a text file.

| Property | Value |
|----------|-------|
| Risk level | Low |
| Confirmation | Never |

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Relative path to the file to read |

### Constraints

- **Relative paths only** -- absolute paths are rejected
- **Max file size**: 100KB (larger files are truncated with a warning)
- **No path traversal** -- `..` segments are blocked
- **No binary files** -- files containing null bytes are rejected
- **Encoding**: UTF-8 with Latin-1 fallback

### Example

```
file_read(path="reports/q4-summary.md")
```

---

## file_write

Write a new file to the output directory (`zhi-output/`).

| Property | Value |
|----------|-------|
| Risk level | High |
| Confirmation | In `approve` mode only |

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Relative path within the output directory |
| `content` | string/object | Yes | File content (format depends on extension) |

### Supported Formats

| Extension | Content type | Description |
|-----------|-------------|-------------|
| `.md`, `.txt` | Plain text string | Written as-is |
| `.json` | Any JSON value | Pretty-printed with 2-space indent |
| `.csv` | `{"headers": [...], "rows": [[...]]}` | Standard CSV with proper escaping |
| `.xlsx` | `{"sheets": [{"name": "...", "headers": [...], "rows": [[...]]}]}` | Multi-sheet Excel workbook |
| `.docx` | `{"content": "markdown string"}` | Markdown converted to Word document |

### Constraints

- **No overwrite** -- existing files cannot be overwritten
- **No absolute paths** -- must be relative within `zhi-output/`
- **No path traversal** -- `..` segments are blocked
- **No symlink escapes** -- resolved paths must stay within the output directory
- **Output cap**: 50KB per tool response

!!! warning "Optional dependencies"
    `.xlsx` output requires `openpyxl` (falls back to CSV if not installed). `.docx` output requires `python-docx` (falls back to `.md` if not installed).

### Example

```
file_write(path="summary.md", content="# Report Summary\n\nKey findings...")
```

---

## file_list

List directory contents with metadata.

| Property | Value |
|----------|-------|
| Risk level | Low |
| Confirmation | Never |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `path` | string | No | `.` | Relative path to list |
| `max_depth` | integer | No | 2 | Recursion depth (range: 1-10) |

### Output Format

Each entry shows:

```
[f] filename.txt                           1.2KB  2026-02-20 14:30
[d] subdirectory/                              -  2026-02-19 09:15
```

- `[f]` = file, `[d]` = directory
- Size in human-readable format (B, KB, MB, GB)
- Modification date in UTC

### Example

```
file_list(path="data", max_depth=3)
```

---

## ocr

Extract text from images and PDFs using Zhipu's OCR API.

| Property | Value |
|----------|-------|
| Risk level | Low |
| Confirmation | Never |

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Path to the image or PDF file |

### Supported Formats

`PDF`, `PNG`, `JPG`, `JPEG`, `GIF`, `WEBP`

### Constraints

- **Max file size**: 20MB
- **Output cap**: 50KB (truncated if larger)
- Absolute paths are allowed (unlike `file_read`)

### Example

```
ocr(path="scanned-invoice.pdf")
```

---

## shell

Execute shell commands with safety checks.

| Property | Value |
|----------|-------|
| Risk level | **Always** (requires confirmation even in `auto` mode) |
| Confirmation | Always |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `command` | string | Yes | - | Shell command to execute |
| `timeout` | integer | No | 30 | Timeout in seconds (range: 1-300) |

### Safety Tiers

#### Blocked (Catastrophic)

These patterns are always rejected -- no confirmation possible:

| Pattern | Reason |
|---------|--------|
| `rm -rf /` | Destroy root filesystem |
| `rm -rf ~` | Destroy home directory |
| `mkfs /dev/` | Format disk device |
| `:(){ :\|:& };:` | Fork bomb |
| `dd if=/dev/zero of=/dev/` | Overwrite disk device |

Also blocked: `eval`, `bash -c`, `sh -c`, `/bin/rm`, `/usr/bin/rm` (bypass prevention).

#### Warned (Destructive)

These commands trigger an extra destructive warning before confirmation:

`rm`, `del`, `rmdir`, `mv`, `chmod`, `chown`, `mkfs`, `dd`, `shred`, `truncate`, `sed -i`, `git reset --hard`, `git clean`

#### Allowed

All other commands require standard confirmation.

### Constraints

- **Output cap**: 100KB (truncated if larger)
- **Process management**: On timeout, kills the entire process group (not just the parent process)
- **Platform support**: Uses `start_new_session` on Unix, `CREATE_NEW_PROCESS_GROUP` on Windows

### Example

```
shell(command="wc -l *.csv", timeout=10)
```

---

## web_fetch

Fetch the text content of a web page.

| Property | Value |
|----------|-------|
| Risk level | Low |
| Confirmation | Never |

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | Yes | URL to fetch (must start with `http://` or `https://`) |

### SSRF Protection

The following targets are blocked to prevent Server-Side Request Forgery:

| Category | Blocked |
|----------|---------|
| Hostnames | `localhost`, `metadata.google.internal`, `metadata` |
| IP ranges | Private: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` |
| Special | Loopback (`127.0.0.1`), link-local (`169.254.x.x`), reserved ranges |

### Constraints

- **Protocols**: HTTP and HTTPS only
- **Output cap**: 50KB
- **Timeout**: 30 seconds
- **Redirects**: Follows redirects automatically
- **HTML processing**: HTML is converted to plain text (scripts and styles removed)
- **User-Agent**: `zhi-cli/1.0`

### Example

```
web_fetch(url="https://example.com/api/data")
```

---

## skill_create

Create a new skill by generating a YAML configuration file.

| Property | Value |
|----------|-------|
| Risk level | High |
| Confirmation | In `approve` mode only |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | Yes | - | Skill name (alphanumeric, hyphens, underscores) |
| `description` | string | Yes | - | Human-readable description |
| `system_prompt` | string | Yes | - | System prompt for the skill |
| `tools` | array[string] | Yes | - | List of tool names the skill can use |
| `model` | string | No | `glm-4-flash` | Model for skill execution |
| `max_turns` | integer | No | 15 | Maximum agent loop turns (clamped to 1-50) |

### Validation Rules

- **Name pattern**: Must match `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`
- **Name length**: Maximum 64 characters
- **No path separators**: `/`, `\`, and `..` are rejected
- **No duplicates**: Cannot create a skill with a name that already exists
- **Tool validation**: All listed tools must exist in the registry

### Example

```
skill_create(
  name="summarize-chinese",
  description="Summarize documents in Chinese",
  system_prompt="You are a Chinese summarization assistant...",
  tools=["file_read", "file_write"]
)
```
