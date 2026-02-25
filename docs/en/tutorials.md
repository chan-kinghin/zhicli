# Tutorials

> zhi is an open-source Python CLI tool powered by Zhipu GLM models. It provides an intelligent terminal assistant with chat, file processing, OCR, and custom skills.

---

## Table of Contents

1. [5-Minute Quickstart](#5-minute-quickstart)
2. [Interactive Chat](#interactive-chat)
3. [File Processing](#file-processing)
4. [Skill System](#skill-system)
5. [Shell Commands](#shell-commands)
6. [Web Content](#web-content)
7. [Composite Skills](#composite-skills)

---

## 5-Minute Quickstart

Get from zero to your first conversation in under 5 minutes.

### Prerequisites

- A Zhipu AI account for your API key ([open.bigmodel.cn](https://open.bigmodel.cn))
- **Windows users** have two options:
    1. Download `zhi.exe` from [GitHub Releases](https://github.com/chan-kinghin/zhicli/releases) (recommended -- no Python needed, the exe bundles Python via PyInstaller)
    2. Install via pip (requires Python 3.10+)
- **macOS users** need Python 3.10+. macOS may ship with an older version. Install a recent one via:
    - `brew install python@3.11` (recommended if you have Homebrew)
    - Or download from [python.org](https://www.python.org/downloads/)
- **Linux users** need Python 3.10+. Most distributions include it:
    - Ubuntu/Debian: `sudo apt install python3 python3-pip`
    - Fedora: `sudo dnf install python3 python3-pip`
    - Arch: `sudo pacman -S python python-pip`

### Step 1: Install

**Windows (exe -- no Python required):**

Download `zhi-*-windows-x64.exe` from [GitHub Releases](https://github.com/chan-kinghin/zhicli/releases), rename it to `zhi.exe`, and run:

```powershell
.\zhi.exe --setup
```

**Windows (pip), macOS, or Linux:**

```bash
pip install zhicli
```

Verify the installation:

```bash
zhi --version
# or on Windows with the exe:
.\zhi.exe --version
```

### Step 2: Configure

Run the setup wizard:

```bash
zhi --setup
```

The wizard walks you through three steps:

```
Welcome to zhi (v0.1.0)

Let's get you set up. This takes about 30 seconds.

Step 1/3: API Key
  Paste your Zhipu API key (get one at open.bigmodel.cn):
  > your-api-key

Step 2/3: Defaults
  Default model for chat [glm-5]:
  Default model for skills [glm-4-flash]:
  Output directory [zhi-output]:

Step 3/3: Quick Demo
  Want to try a sample skill? [Y/n]:

Setup complete. Type /help to see available commands.
```

Alternatively, set the API key via environment variable:

```bash
# Linux / macOS
export ZHI_API_KEY="your-api-key"

# Windows (PowerShell)
$env:ZHI_API_KEY = "your-api-key"
```

### Step 3: Start Chatting

**Interactive mode** -- launch the REPL:

```bash
zhi
```

**One-shot mode** -- ask a single question and exit:

```bash
zhi -c "What is machine learning?"
```

**Run a skill** -- process a file with a built-in skill:

```bash
zhi run summarize document.txt
```

That's it. You are ready to go.

---

## Interactive Chat

### Entering the REPL

```bash
zhi
```

```
Welcome to zhi. Type /help for commands.
You [approve]:
```

The `[approve]` label in the prompt shows the current permission mode.

### Slash Commands

Type `/help` to see all available commands:

```
Available commands:
  /help              Show this help message
  /auto              Switch to auto mode (no permission prompts)
  /approve           Switch to approve mode (default)
  /model <name>      Switch model (glm-5, glm-4-flash, glm-4-air)
  /think             Enable thinking mode
  /fast              Disable thinking mode
  /run <skill> [args]  Run a skill
  /skill list|new|show|edit|delete  Manage skills
  /reset             Clear conversation history
  /undo              Remove last exchange
  /usage             Show token/cost stats
  /verbose           Toggle verbose output
  /exit              Exit zhi
```

### Permission Modes

zhi has two permission modes:

- **approve** (default): You must confirm before zhi writes files or runs shell commands.
- **auto**: Skips confirmation prompts and executes operations automatically.

```
You [approve]: /auto
Mode switched to auto

You [auto]: /approve
Mode switched to approve
```

!!! warning
    Shell commands always require confirmation, even in auto mode. This is a safety feature that cannot be bypassed.

### Model Switching

zhi supports three models:

| Model | Type | Use Case |
|-------|------|----------|
| `glm-5` | Premium | Default chat model -- most capable, higher cost |
| `glm-4-flash` | Economy | Skill execution -- fast and inexpensive |
| `glm-4-air` | Economy | Lightweight alternative |

Check and switch models:

```
You [approve]: /model
Current model: glm-5. Available: glm-5, glm-4-flash, glm-4-air

You [approve]: /model glm-4-flash
Model switched to glm-4-flash
```

### Thinking Mode

Enable thinking mode to see the model's reasoning process (GLM-5 only):

```
You [approve]: /think
Thinking mode enabled

You [approve]: Explain why the sky is blue

You [approve]: /fast
Thinking mode disabled
```

### Multi-line Input

Add `\` at the end of a line to continue on the next line:

```
You [approve]: Write a Python function that \
...  accepts a list parameter and \
...  returns the maximum value
```

### Managing Conversation History

Undo the last exchange:

```
You [approve]: /undo
Last exchange removed
```

Clear all history:

```
You [approve]: /reset
Conversation cleared
```

### Usage Statistics

```
You [approve]: /usage
```

Shows token counts and estimated cost for the current session.

### Exiting

```
You [approve]: /exit
Goodbye!
```

You can also press `Ctrl+D` to exit, or `Ctrl+C` to cancel the current input.

!!! tip
    - Input history is saved automatically. Use the up/down arrow keys to browse previous inputs.
    - Lines containing sensitive keywords (api_key, password, token) are excluded from history.
    - Tab completion works for slash commands and model names.
    - Switching models only affects the current session -- it does not modify the config file.

---

## File Processing

### Reading Text Files

Ask zhi to read and work with files in conversation:

```
You [approve]: Read README.md and summarize its contents
```

zhi calls the `file_read` tool to load the file, then generates a summary.

**file_read characteristics:**

- Only reads files within the current working directory (relative paths)
- Maximum file size: 100KB (larger files are truncated)
- Auto-detects encoding, defaults to UTF-8
- Cannot read binary files

### Listing Directory Contents

```
You [approve]: List all files in the current directory
```

zhi calls the `file_list` tool and displays filenames, sizes, and modification times.

### OCR: Extracting Text from Images and PDFs

Extract text from scanned documents or images:

```
You [approve]: Extract the text from invoice.png

You [approve]: Extract text from report.pdf and summarize the key points
```

**Supported formats:**

- Images: PNG, JPG, JPEG, GIF, WEBP
- Documents: PDF
- Maximum file size: 20MB

### Writing Files

All file output is saved to the `zhi-output/` directory:

```
You [approve]: Write that summary as a Markdown file
```

In approve mode, zhi asks for confirmation before creating the file.

**Supported output formats:**

| Format | Extension | Content |
|--------|-----------|---------|
| Plain text | `.md`, `.txt` | Direct text |
| JSON | `.json` | Any JSON structure |
| CSV | `.csv` | Headers + rows |
| Excel | `.xlsx` | Sheet data |
| Word | `.docx` | Markdown text |

### Combining Read + Process + Write

```
You [approve]: Read data.csv, analyze the trends, then write an analysis report to report.md
```

zhi chains file_read, analysis, and file_write calls automatically.

!!! info
    - `file_write` creates new files only -- it cannot overwrite existing files.
    - All output goes to `zhi-output/`, keeping your original files safe.
    - Paths cannot contain `..`, preventing writes outside the working directory.
    - Excel (.xlsx) and Word (.docx) formats are supported out of the box.

---

## Skill System

### What Are Skills?

Skills are predefined YAML configurations that bundle a system prompt, allowed tools, and model settings into a reusable workflow. Run them with a single command instead of typing instructions each time. Skills use the `glm-4-flash` model by default, costing roughly 10% of what GLM-5 chat costs.

### Built-in Skills

zhi ships with **15 built-in skills** -- 9 single-purpose skills and 6 composite skills that chain multiple single-purpose skills together.

#### Single-Purpose Skills (9)

| Skill | Description | Usage |
|-------|-------------|-------|
| `summarize` | Summarize a document | `zhi run summarize report.txt` |
| `translate` | Translate a document (default: to Chinese) | `zhi run translate readme-en.md` |
| `extract-text` | OCR text from PDF/images | `zhi run extract-text scan.pdf` |
| `extract-table` | Extract tables from documents | `zhi run extract-table invoice.pdf` |
| `analyze` | Deep structural analysis of a document | `zhi run analyze proposal.md` |
| `proofread` | Grammar, spelling, style corrections | `zhi run proofread draft.md` |
| `reformat` | Convert between document formats | `zhi run reformat notes.txt` |
| `meeting-notes` | Structure raw notes into formal minutes | `zhi run meeting-notes notes.txt` |
| `compare` | Diff two documents and highlight changes | `zhi run compare v1.md v2.md` |

#### Composite Skills (6)

These chain multiple single-purpose skills into multi-step workflows. See the [Composite Skills](#composite-skills) section below for details.

| Skill | Pipeline | Usage |
|-------|----------|-------|
| `contract-review` | analyze + compare + proofread | `zhi run contract-review contract.pdf` |
| `daily-digest` | file_list + summarize (batch) | `zhi run daily-digest ./reports/` |
| `invoice-to-excel` | extract-table + reformat | `zhi run invoice-to-excel invoices/` |
| `meeting-followup` | meeting-notes + summarize + translate | `zhi run meeting-followup notes.txt` |
| `report-polish` | proofread + analyze + reformat | `zhi run report-polish draft.md` |
| `translate-proofread` | translate + proofread | `zhi run translate-proofread doc.md` |

### Listing Installed Skills

```
You [approve]: /skill list
```

### Running Skills

From the command line:

```bash
zhi run summarize report.txt
```

From interactive mode:

```
You [approve]: /run summarize report.txt
```

### Creating Custom Skills

**Option 1: Let zhi create it for you**

```
You [approve]: Create a code review skill called code-review that reads source code and suggests improvements
```

zhi generates the YAML configuration file automatically.

**Option 2: Write YAML manually**

Create a `.yaml` file in your config directory's `skills/` folder:

```yaml
name: code-review
description: Review source code and suggest improvements
model: glm-4-flash
system_prompt: |
  You are an experienced code reviewer. Read the provided source code
  and give actionable suggestions for improvement. Focus on:
  - Code quality and readability
  - Potential bugs
  - Performance issues
  Output your review as structured markdown.
tools:
  - file_read
  - file_write
max_turns: 10
input:
  description: Source code file to review
  args:
    - name: file
      type: file
      required: true
output:
  description: Code review report in markdown
  directory: zhi-output
```

### YAML Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill name. Letters, digits, hyphens, underscores only. Max 64 chars. |
| `description` | Yes | Brief description of the skill |
| `system_prompt` | Yes | System prompt that guides model behavior |
| `tools` | Yes | List of tools the skill can access |
| `model` | No | Model to use. Default: `glm-4-flash` |
| `max_turns` | No | Maximum execution turns. Default: 15 |
| `input` | No | Input parameter definitions |
| `output` | No | Output config (description and directory) |

### Available Tools

| Tool | Function | Risk Level |
|------|----------|------------|
| `file_read` | Read text files | Low |
| `file_write` | Write new files to zhi-output/ | High |
| `file_list` | List directory contents | Low |
| `ocr` | OCR for images and PDFs | Low |
| `shell` | Execute shell commands | High |
| `web_fetch` | Fetch web page content | Low |
| `skill_create` | Create new skills | High |
| `ask_user` | Ask the user a question mid-execution | Low |

### Managing Skills

```
You [approve]: /skill show code-review   # View skill details
You [approve]: /skill delete code-review # Delete a custom skill
```

!!! info
    - Skill names must match `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`
    - Each skill can only access tools declared in its `tools` list
    - Skill output defaults to the `zhi-output/` directory
    - Only user-created skill YAML files can be deleted; built-in skills are protected

---

## Shell Commands

### Basic Usage

Ask zhi to run commands in conversation:

```
You [approve]: Run ls -la to see the current directory
```

zhi displays the command and waits for confirmation:

```
zhi wants to run: ls -la
Allow? [y/n]:
```

Type `y` to allow, `n` to deny.

### Three-Layer Safety Model

#### 1. Always Requires Confirmation

Shell commands require user confirmation regardless of permission mode. Even in auto mode, you must approve every command.

#### 2. Destructive Command Warnings

These commands trigger an extra warning:

- File deletion: `rm`, `del`, `rmdir`
- File moves: `mv`
- Permission changes: `chmod`, `chown`
- Disk operations: `mkfs`, `dd`, `shred`, `truncate`
- In-place edits: `sed -i`
- Git danger zone: `git reset --hard`, `git clean`

#### 3. Catastrophic Commands Blocked

These commands are permanently blocked and cannot be executed:

- `rm -rf /` or `rm -rf ~`
- `rm -rf /*` or `rm -rf ~/`
- `mkfs /dev/...`
- Fork bombs
- `dd if=/dev/zero of=/dev/...`

### Timeout

Shell commands have a default timeout of 30 seconds, with a maximum of 300 seconds (5 minutes). When a command times out, zhi kills the entire process group to prevent leftover processes.

### Output Limits

Command output is capped at 100KB. Anything beyond that is truncated.

### Practical Examples

```
You [approve]: Check the system's Python version

You [approve]: Count lines of code in the src/ directory

You [approve]: Run pytest and tell me the results
```

!!! warning
    Never let the AI run commands you do not understand, even though zhi always asks for confirmation. Cross-platform support: uses `CREATE_NEW_PROCESS_GROUP` on Windows, `start_new_session` on Unix.

---

## Web Content

### Fetching Web Pages

```
You [approve]: Fetch the content from https://example.com
```

zhi calls the `web_fetch` tool to retrieve the page content, automatically converting HTML to plain text.

### Analyzing Web Content

```
You [approve]: Fetch this page and summarize the key points: https://example.com/article
```

zhi fetches the content first, then uses the GLM model to analyze it.

### Fetching and Saving

```
You [approve]: Scrape https://example.com/data, extract the key data, and save it as a CSV file
```

zhi combines `web_fetch` and `file_write` to complete the task.

### Using Web Fetch in Skills

Create a skill that includes `web_fetch` for automated web content processing:

```yaml
name: web-summary
description: Fetch and summarize web pages
model: glm-4-flash
system_prompt: |
  Fetch the given URL, read the content, and produce a concise
  summary. Save the summary as a markdown file.
tools:
  - web_fetch
  - file_write
max_turns: 5
```

Then run it:

```bash
zhi run web-summary
```

!!! info
    - URLs must start with `http://` or `https://`
    - Request timeout: 30 seconds
    - Response content limit: 50KB (excess is truncated)
    - HTML pages are automatically stripped of tags and converted to plain text
    - `web_fetch` follows redirects automatically
    - SSRF protection is built in

---

## Composite Skills

Composite skills chain multiple single-purpose skills into automated multi-step workflows. They still run on `glm-4-flash`, keeping costs low.

### contract-review

**Pipeline:** analyze + compare + proofread

Reviews a contract document through three lenses: structural analysis to identify key clauses and risks, optional comparison with a previous version to highlight changes, and proofreading to catch ambiguous wording.

```bash
# Review a single contract
zhi run contract-review contract.pdf

# Compare two versions
zhi run contract-review contract-v2.pdf contract-v1.pdf
```

**Output:** A comprehensive review report with executive summary, structural analysis, version changes (if applicable), language issues, risk assessment, and negotiation recommendations.

### daily-digest

**Pipeline:** file_list + summarize (batch)

Scans all documents in a folder and produces a single combined digest report with individual summaries and cross-document insights.

```bash
zhi run daily-digest ./inbox/
```

**Output:** A digest report listing each document's summary, common themes, contradictions, and suggested follow-up actions.

!!! tip
    Supported file types include `.txt`, `.md`, `.pdf`, `.csv`, `.docx`, `.xlsx`, `.png`, and `.jpg`. Binary and system files are skipped automatically.

### invoice-to-excel

**Pipeline:** extract-table + reformat

Processes invoice files (PDF, image, or text) through OCR table extraction, then consolidates all line items into a structured Excel spreadsheet.

```bash
# Single invoice
zhi run invoice-to-excel invoice.pdf

# Batch process a folder of invoices
zhi run invoice-to-excel ./invoices/
```

**Output:** An Excel file with two sheets -- "Line Items" (one row per item across all invoices) and "Invoice Summary" (one row per invoice with totals). Dates are normalized to YYYY-MM-DD, currencies are cleaned, and totals are validated.

### meeting-followup

**Pipeline:** meeting-notes + summarize + translate

Takes raw meeting notes and produces a complete follow-up package: structured minutes, an executive summary for leadership, and an optional translated summary.

```bash
# Basic follow-up
zhi run meeting-followup raw-notes.txt

# With translation
zhi run meeting-followup raw-notes.txt --to english
```

**Output:** Three files -- full meeting minutes, a 1-page executive summary, and (optionally) a translated summary. Action items appear in both the full minutes and the summary.

### report-polish

**Pipeline:** proofread + analyze + reformat

Takes a draft document and produces a publication-ready version by proofreading for language issues, analyzing structure and flow, and producing a clean final version.

```bash
zhi run report-polish draft-report.md

# Specify output format
zhi run report-polish draft.md --format docx
```

**Output:** Two files -- the polished document and a change log showing a before/after quality score, all corrections made, structural improvements, and remaining suggestions.

### translate-proofread

**Pipeline:** translate + proofread

Translates a document and then proofreads the translation to ensure it reads naturally in the target language.

```bash
# Default: translate to Chinese
zhi run translate-proofread article-en.md

# Specify target language
zhi run translate-proofread article.md --to english
```

**Output:** Two files -- the polished translation and a quality report with the detected source language, translation quality score, issues found and fixed, and passages that may need human review.

---

## Appendix

### Pipe Mode

Pipe text directly into zhi:

```bash
echo "Translate to English: hello world" | zhi

cat article.txt | zhi
```

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
zhi --debug
```

### Disabling Color Output

For terminals that do not support color:

```bash
zhi --no-color
```

Or set the environment variable:

```bash
export NO_COLOR=1
```

### Configuration Reference

The config file is located in your system config directory as `config.yaml`:

```yaml
api_key: "your-api-key"
default_model: "glm-5"
skill_model: "glm-4-flash"
output_dir: "zhi-output"
max_turns: 30
log_level: "INFO"
```

**Config file locations:**

- macOS: `~/Library/Application Support/zhi/config.yaml`
- Linux: `~/.config/zhi/config.yaml`
- Windows: `%APPDATA%\zhi\config.yaml`

**Environment variable overrides:**

| Variable | Config Field |
|----------|-------------|
| `ZHI_API_KEY` | `api_key` |
| `ZHI_DEFAULT_MODEL` | `default_model` |
| `ZHI_OUTPUT_DIR` | `output_dir` |
| `ZHI_LOG_LEVEL` | `log_level` |

The environment variable `ZHI_API_KEY` takes priority over the config file.

### FAQ

**Q: "No API key configured" error**

Run `zhi --setup` or set the `ZHI_API_KEY` environment variable.

**Q: File write fails with "File already exists"**

`file_write` cannot overwrite existing files. Delete or rename the file in `zhi-output/` and try again.

**Q: OCR returns empty results**

Confirm the file format is supported (PDF, PNG, JPG, JPEG, GIF, WEBP) and the file is under 20MB. Image clarity affects recognition quality.

**Q: Shell command blocked**

Certain dangerous commands (like `rm -rf /`) are permanently blocked. This is a safety feature that cannot be bypassed.

**Q: Excel/Word output fails**

Excel (.xlsx) and Word (.docx) are included in the default install. Make sure you're on the latest version: `pip install --upgrade zhicli`.
