# Skills Reference

zhi ships with **15 built-in skills** organized into two categories: single-purpose skills that perform one task, and composite skills that orchestrate multiple skills together.

## Single-Purpose Skills

### summarize

Summarize a text file or document into a concise markdown overview.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `file_write` |
| Max turns | 5 |

**Usage:**

```bash
zhi run summarize report.txt
```

**Output:** A markdown summary saved to `zhi-output/` containing key points, main arguments, and important details.

---

### translate

Translate text between languages, defaulting to Chinese (Simplified).

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `file_write` |
| Max turns | 5 |

**Arguments:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file` | file | No | - | File to translate |
| `text` | string | No | - | Text to translate |
| `to` | string | No | `chinese` | Target language |

**Usage:**

```bash
zhi run translate readme-en.md
```

---

### extract-text

Extract text from PDF or image files using OCR and save as plain text.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `ocr`, `file_write`, `file_list` |
| Max turns | 5 |

**Usage:**

```bash
zhi run extract-text invoice.pdf
```

**Output:** A cleaned `.txt` file preserving document structure (headings, paragraphs, lists). Page headers/footers are removed, and tables are rendered as aligned text.

---

### extract-table

Extract tables from documents and save as CSV or Excel.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `ocr`, `file_read`, `file_write`, `file_list` |
| Max turns | 8 |

**Usage:**

```bash
zhi run extract-table report.pdf
```

**Output:** One or more CSV files with proper column headers. Multiple tables are saved as separate files (`table1.csv`, `table2.csv`) or combined if they share the same schema.

!!! tip "Excel output"
    Request `.xlsx` output in your prompt and the skill will produce Excel files instead of CSV.

---

### analyze

Deep analysis of a document with structured insights.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `ocr`, `file_write`, `file_list` |
| Max turns | 8 |

**Usage:**

```bash
zhi run analyze proposal.md
```

**Output:** A markdown report with four sections:

1. **Document Overview** -- type, length, structure, primary language
2. **Key Findings** -- main topics, arguments, data points
3. **Structure Analysis** -- organization, logical flow, gaps
4. **Actionable Takeaways** -- implied decisions, open questions, follow-up steps

---

### proofread

Proofread a document and output a correction report.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `ocr`, `file_write` |
| Max turns | 5 |

**Usage:**

```bash
zhi run proofread draft.md
```

**Output:** A markdown report containing:

- Overall quality score (out of 10)
- Per-issue corrections with location, original text, corrected text, and error type (spelling / grammar / punctuation / style / clarity)
- Summary of recurring patterns

---

### reformat

Convert documents between formats.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `ocr`, `file_write`, `file_list` |
| Max turns | 8 |

**Arguments:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file` | file | Yes | - | File to convert |
| `format` | string | No | `markdown` | Target format |

**Supported conversions:**

| From | To |
|------|----|
| Plain text | Markdown |
| Markdown | Plain text |
| CSV | Markdown table |
| CSV | Excel (`.xlsx`) |
| Any text | CSV |
| Any text | JSON |
| PDF/Image (via OCR) | Markdown / Text / CSV |

**Usage:**

```bash
zhi run reformat data.csv
```

---

### meeting-notes

Structure raw meeting notes into organized minutes.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `ocr`, `file_write` |
| Max turns | 5 |

**Usage:**

```bash
zhi run meeting-notes notes.txt
```

**Output:** Structured markdown meeting minutes containing:

- **Attendees** -- list of participants
- **Agenda Items** -- key discussion points and decisions per topic
- **Action Items** -- table with task, owner, and deadline
- **Key Decisions** -- numbered list
- **Next Steps** -- follow-up items and next meeting date

---

### compare

Compare two documents and highlight differences.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `ocr`, `file_write`, `file_list` |
| Max turns | 8 |

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file` | file | Yes | First file |
| `file2` | file | Yes | Second file |

**Usage:**

```bash
zhi run compare v1.md v2.md
```

**Output:** A markdown diff report with comparison summary, added/removed/modified sections, and unchanged sections. Focuses on meaningful differences and ignores whitespace-only changes.

---

## Composite Skills

Composite skills orchestrate multiple single-purpose skills using `skill_<name>` tool wrappers. They have higher turn limits to accommodate multi-step workflows.

### contract-review

Multi-step contract analysis combining analysis, comparison, and proofreading.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `ocr`, `file_write`, `file_list`, `skill_analyze`, `skill_compare`, `skill_proofread` |
| Max turns | 15 |

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file` | file | Yes | Contract to review |
| `file2` | file | No | Previous version for comparison |

**Usage:**

```bash
zhi run contract-review contract-v2.pdf contract-v1.pdf
```

**Output:** A comprehensive review report containing:

- Executive summary with overall assessment
- Structural analysis (key clauses, obligations, risks)
- Version comparison (if previous version provided)
- Language and consistency issues
- Risk assessment (liability, indemnity, termination)
- Numbered recommendations

---

### daily-digest

Batch-summarize all documents in a folder into a single digest.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_list`, `file_read`, `ocr`, `file_write`, `skill_summarize` |
| Max turns | 15 |

**Supported file types:** `.txt`, `.md`, `.pdf`, `.csv`, `.docx`, `.xlsx`, `.png`, `.jpg`

**Usage:**

```bash
zhi run daily-digest ./reports/
```

**Output:** A single markdown digest with:

- Overview (document count, key themes)
- Individual summaries per document
- Cross-document insights (common themes, contradictions, follow-up actions)

---

### invoice-to-excel

OCR invoices and consolidate line items into an Excel spreadsheet.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_list`, `file_read`, `ocr`, `file_write`, `skill_extract-table`, `skill_reformat` |
| Max turns | 15 |

**Usage:**

```bash
zhi run invoice-to-excel invoices/
```

**Output:** An Excel file with:

- **Sheet 1 "Line Items"**: Invoice #, Date, Vendor, Item, Quantity, Unit Price, Amount, Tax, Total
- **Sheet 2 "Invoice Summary"** (multiple invoices): Invoice #, Date, Vendor, Subtotal, Tax, Total, Status

!!! info "Data normalization"
    Currencies are normalized (symbols removed, consistent decimals). Dates are formatted as `YYYY-MM-DD`. Missing fields show `N/A`.

---

### meeting-followup

Generate structured minutes, executive summary, and optional translation from raw meeting notes.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `ocr`, `file_write`, `skill_meeting-notes`, `skill_summarize`, `skill_translate` |
| Max turns | 15 |

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file` | file | Yes | Raw meeting notes |
| `translate_to` | string | No | Target language for summary translation |

**Usage:**

```bash
zhi run meeting-followup standup-notes.txt
```

**Output:** Up to three files:

1. `[meeting]-minutes.md` -- full structured meeting minutes
2. `[meeting]-summary.md` -- executive summary (1 page max)
3. `[meeting]-summary-en.md` -- translated summary (if applicable)

---

### report-polish

Proofread, analyze structure, and produce a polished final version of a document.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `ocr`, `file_write`, `skill_proofread`, `skill_analyze`, `skill_reformat` |
| Max turns | 12 |

**Arguments:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file` | file | Yes | - | Draft document |
| `format` | string | No | `markdown` | Output format (markdown, docx, txt) |

**Usage:**

```bash
zhi run report-polish draft-report.md
```

**Output:** Two files:

1. `[filename]-final.[ext]` -- polished document
2. `[filename]-changes.md` -- change log with before/after quality scores, language fixes, structural improvements, and remaining suggestions

---

### translate-proofread

Translate a document and proofread the translation for quality.

| Property | Value |
|----------|-------|
| Model | `glm-4-flash` |
| Tools | `file_read`, `ocr`, `file_write`, `skill_translate`, `skill_proofread` |
| Max turns | 12 |

**Arguments:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file` | file | Yes | - | Document to translate |
| `to` | string | No | `chinese` | Target language |

**Usage:**

```bash
zhi run translate-proofread whitepaper.md
```

**Output:** Two files:

1. `[filename]-translated.[ext]` -- polished final translation
2. `[filename]-translation-report.md` -- quality report with detected source language, quality score (1-10), issues fixed, and passages needing human review

---

## Creating Custom Skills

You can create custom skills by writing YAML configuration files. Place them in your user skills directory or use the `skill_create` tool.

```yaml
name: my-skill
description: What this skill does
model: glm-4-flash
system_prompt: |
  Your instructions to the model...
tools:
  - file_read
  - file_write
max_turns: 10
```

!!! info "Skill naming rules"
    Skill names must match `^[a-zA-Z0-9][a-zA-Z0-9_-]*$` and be at most 64 characters long. No spaces, slashes, or special characters.
