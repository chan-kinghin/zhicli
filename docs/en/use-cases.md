# Use Cases

> Real-world scenarios showing how zhi CLI fits into your workflow.

---

## Table of Contents

- [I. Daily Office](#i-daily-office)
  - [1.1 Summarize Meeting Minutes](#11-summarize-meeting-minutes)
  - [1.2 Translate Documents](#12-translate-documents)
  - [1.3 Generate Weekly/Daily Reports](#13-generate-weeklydaily-reports)
- [II. Data Extraction & Comparison](#ii-data-extraction-comparison)
  - [2.1 Compare Two Document Versions](#21-compare-two-document-versions)
  - [2.2 Extract Key Figures from Financial Reports](#22-extract-key-figures-from-financial-reports)
  - [2.3 Clean Up a Contact List](#23-clean-up-a-contact-list)
  - [2.4 Cross-Document Summary](#24-cross-document-summary)
- [III. Content Creation](#iii-content-creation)
  - [3.1 Article Summary and Rewrite](#31-article-summary-and-rewrite)
  - [3.2 Multilingual Content Translation](#32-multilingual-content-translation)
  - [3.3 Markdown Formatting](#33-markdown-formatting)
- [IV. Data Processing](#iv-data-processing)
  - [4.1 PDF/Image OCR Text Extraction](#41-pdfimage-ocr-text-extraction)
  - [4.2 CSV/Excel Data Cleanup](#42-csvexcel-data-cleanup)
  - [4.3 Web Content Scraping and Analysis](#43-web-content-scraping-and-analysis)
- [V. Custom Skills](#v-custom-skills)
  - [5.1 Contract Review Skill](#51-contract-review-skill)
  - [5.2 Email Draft Skill](#52-email-draft-skill)
  - [5.3 Data Analysis Skill](#53-data-analysis-skill)
- [VI. Developer Workflows](#vi-developer-workflows)
  - [6.1 Code Review with Custom Skill](#61-code-review-with-custom-skill)
  - [6.2 Generate Test Data](#62-generate-test-data)
  - [6.3 Summarize Git History](#63-summarize-git-history)
  - [6.4 Cost-Effective Batch Processing](#64-cost-effective-batch-processing)

---

## I. Daily Office

### 1.1 Summarize Meeting Minutes

**Scenario:** After a product review meeting, you have a lengthy transcript and need to produce a concise summary to share with the team.

**Steps:**

Use the built-in `summarize` skill:

```bash
$ zhi run summarize product-review-notes.txt
```

zhi reads the file and generates a structured summary, saving it to `zhi-output/`:

```
[file_read] Reading: product-review-notes.txt (12.3KB)
[file_write] Writing: product-review-notes-summary.md (1.8KB)

File saved: zhi-output/product-review-notes-summary.md
```

**Result:** A Markdown summary containing key decisions, action items, and owners. Typically 10-20% of the original length.

For more specific instructions, use interactive mode:

```bash
$ zhi
You [approve]: Summarize this meeting transcript, focusing on action items and deadlines
```

---

### 1.2 Translate Documents

**Scenario:** You received a technical specification in English and need a Chinese translation for team review.

**Steps:**

Use the built-in `translate` skill:

```bash
$ zhi run translate api-specification.md
```

The default target language is Chinese. For other directions:

```bash
$ zhi -c "Translate project-intro.md to English, keeping Markdown formatting intact"
```

Output:

```
[file_read] Reading: api-specification.md (8.5KB)
[file_write] Writing: api-specification-translated.md (9.2KB)

File saved: zhi-output/api-specification-translated.md
```

**Result:** A complete translation that preserves document structure (headings, code blocks, lists). Technical terms like API, JSON, and HTTP are kept in English.

---

### 1.3 Generate Weekly/Daily Reports

**Scenario:** Friday afternoon, you need a weekly report based on your work notes and Git history.

**Steps:**

```bash
$ zhi
You [approve]: Generate a weekly report from my work notes, including completed items, \
...  in-progress items, and plans for next week
```

```
[file_read] Reading: weekly-notes.md (3.2KB)
  → Allow reading this file? (y/n) y
[file_write] Writing: weekly-report-2026-02-23.md (1.5KB)
  → Allow creating this file? (y/n) y

File saved: zhi-output/weekly-report-2026-02-23.md
```

**Result:** A formatted report organized into "Completed", "In Progress", and "Next Week" sections.

Combine with Git history using pipes:

```bash
$ git log --oneline --since="last monday" | zhi -c "Generate a work summary based on these Git commits"
```

---

## II. Data Extraction & Comparison

### 2.1 Compare Two Document Versions

**Scenario:** A client sent a revised contract. You need to quickly identify all changes between versions.

**Steps:**

Use the built-in `compare` skill:

```bash
$ zhi run compare contract-v1.md contract-v2.md
```

zhi compares both documents paragraph by paragraph:

```
[file_read] Reading: contract-v1.md (6.2KB)
[file_read] Reading: contract-v2.md (6.8KB)
[file_write] Writing: contract-diff-report.md (2.5KB)

File saved: zhi-output/contract-diff-report.md
```

**Result:** A structured diff report showing added, removed, and modified content with a comparison table highlighting specific changes and their locations.

---

### 2.2 Extract Key Figures from Financial Reports

**Scenario:** You received a quarterly financial report as a PDF and need to extract key metrics for management.

**Steps:**

```bash
$ zhi -c "Read quarterly-report.pdf, extract revenue, profit, and YoY growth figures, save as a spreadsheet"
```

```
[ocr] Recognizing: quarterly-report.pdf (4.5MB)
[file_write] Writing: financial-metrics.xlsx (3.2KB)

File saved: zhi-output/financial-metrics.xlsx
```

**Result:** Key financial data extracted from the PDF and organized into a structured table with calculated growth percentages.

---

### 2.3 Clean Up a Contact List

**Scenario:** You have a messy CSV of client contacts with duplicates and inconsistent formatting.

**Steps:**

```bash
$ zhi -c "Read contacts.csv, remove duplicates, sort by company name, save as a new Excel file"
```

```
[file_read] Reading: contacts.csv (8.6KB)
[file_write] Writing: contacts-cleaned.xlsx (5.1KB)

File saved: zhi-output/contacts-cleaned.xlsx
```

**Result:** Duplicates removed (matched by name + phone), formatting unified, and records sorted alphabetically by company name. The original CSV is untouched.

---

### 2.4 Cross-Document Summary

**Scenario:** You have multiple project progress reports and need a consolidated overview.

**Steps:**

```bash
$ zhi
You [approve]: Read project-A-status.md, project-B-status.md, and project-C-status.md. \
...  Extract completion progress, risks, and next steps from each, then produce a summary report
```

```
[file_read] Reading: project-A-status.md (3.5KB)
[file_read] Reading: project-B-status.md (4.1KB)
[file_read] Reading: project-C-status.md (2.8KB)
[file_write] Writing: project-summary.md (3.6KB)

File saved: zhi-output/project-summary.md
```

**Result:** A consolidated report with a progress overview table, risk items, and action plans extracted from all three reports.

---

## III. Content Creation

### 3.1 Article Summary and Rewrite

**Scenario:** You need to condense a long article or rewrite it for a different audience.

**Steps:**

Generate a summary:

```bash
$ zhi run summarize tech-article.md
```

Rewrite for a different audience:

```bash
$ zhi
You [approve]: Read tech-article.md and rewrite it in plain language for a non-technical audience
```

```
[file_read] Reading: tech-article.md (6.8KB)
[file_write] Writing: tech-article-simplified.md (5.2KB)

File saved: zhi-output/tech-article-simplified.md
```

**Result:** A rewritten version with adjusted language and technical depth, preserving the core message. The original file is not modified.

---

### 3.2 Multilingual Content Translation

**Scenario:** Your product needs bilingual release notes published simultaneously.

**Steps:**

```bash
$ zhi -c "Read changelog-v2.5.md, translate to English, keep Markdown formatting and version numbers"
```

```
[file_read] Reading: changelog-v2.5.md (2.1KB)
[file_write] Writing: changelog-v2.5-en.md (2.3KB)

File saved: zhi-output/changelog-v2.5-en.md
```

**Result:** An accurate, fluent translation with formatting fully preserved. Version numbers, code snippets, and variable names are left untranslated.

---

### 3.3 Markdown Formatting

**Scenario:** You have raw, unstructured notes that need to be formatted into proper Markdown.

**Steps:**

```bash
$ zhi
You [approve]: Read meeting-notes-raw.txt, organize into well-formatted Markdown with headings and lists
```

```
[file_read] Reading: meeting-notes-raw.txt (1.8KB)
[file_write] Writing: meeting-notes-formatted.md (2.0KB)

File saved: zhi-output/meeting-notes-formatted.md
```

**Result:** A clean Markdown file with proper heading hierarchy, ordered/unordered lists, and block quotes. Ready to paste into Notion, GitHub, or any Markdown-compatible platform.

---

## IV. Data Processing

### 4.1 PDF/Image OCR Text Extraction

**Scenario:** You have a scanned contract PDF or a photo of a whiteboard that needs to be converted to editable text.

**Steps:**

Extract text from a PDF:

```bash
$ zhi -c "Use OCR to extract text from contract-scan.pdf, save as a text file"
```

```
[ocr] Recognizing: contract-scan.pdf (3.2MB)
[file_write] Writing: contract-content.txt (8.5KB)

File saved: zhi-output/contract-content.txt
```

Extract text from an image:

```bash
$ zhi -c "Extract text from whiteboard-photo.jpg, organize into a bulleted list"
```

**Result:** Text extracted from PDF or image files, cleaned up, and formatted as requested. Supports PDF, PNG, JPG, GIF, WEBP. Maximum file size: 20MB.

Batch processing:

```bash
$ zhi
You [approve]: Extract text from screenshot1.png and screenshot2.png, combine into a single document
```

---

### 4.2 CSV/Excel Data Cleanup

**Scenario:** You have a messy CSV that needs cleaning, aggregation, and conversion to Excel.

**Steps:**

```bash
$ zhi
You [approve]: Read sales-data-raw.csv, aggregate sales by region, generate a new Excel file
```

```
[file_read] Reading: sales-data-raw.csv (15.6KB)
[file_write] Writing: sales-by-region.xlsx (4.8KB)

File saved: zhi-output/sales-by-region.xlsx
```

CSV-to-CSV processing also works:

```bash
$ zhi -c "Read user-list.csv, remove duplicates, sort by registration date, save as a new CSV"
```

**Result:** Data cleaned, aggregated, or transformed and saved in the requested format. Excel (.xlsx) and Word (.docx) output are supported out of the box.

---

### 4.3 Web Content Scraping and Analysis

**Scenario:** You need to pull information from a web page and organize it into a report.

**Steps:**

```bash
$ zhi
You [approve]: Fetch https://example.com/tech-trends-2026, extract key points, and save as a summary
```

```
[web_fetch] Fetching: https://example.com/tech-trends-2026 (28.5KB)
[file_write] Writing: tech-trends-summary.md (2.1KB)

File saved: zhi-output/tech-trends-summary.md
```

**Result:** Main content extracted from the web page (ads and navigation stripped), organized into a structured summary. Web content is capped at 50KB.

Combine with translation:

```bash
$ zhi -c "Fetch https://example.com/release-notes, translate to Chinese, and save"
```

---

## V. Custom Skills

zhi lets you define reusable skills as YAML files. Once created, they work just like built-in features. Skills run on `glm-4-flash`, costing roughly 10% of interactive chat.

### 5.1 Contract Review Skill

**Scenario:** Your legal team needs a standardized checklist applied to every new contract.

**Steps:**

Let zhi create the skill:

```bash
$ zhi
You [approve]: Create a contract review skill that checks for: key clauses, \
...  deadlines, liability limits, termination conditions, and payment terms
```

```
[skill_create] Creating skill: contract-review
  → Allow creating this skill? (y/n) y

Skill 'contract-review' created
```

Use the skill:

```bash
$ zhi run contract-review vendor-agreement.md
```

**Result:** A structured review report with pass/fail/attention status for each checklist item, plus specific recommendations.

!!! tip
    zhi also ships with a built-in `contract-review` composite skill that chains analyze, compare, and proofread together. Use the built-in one for comprehensive reviews, or create a custom one tailored to your specific checklist.

---

### 5.2 Email Draft Skill

**Scenario:** You send multiple similar business emails daily and want to automate draft generation.

**Steps:**

```bash
$ zhi
You [approve]: Create an email draft skill that generates formal business emails from brief descriptions
```

```
[skill_create] Creating skill: email-draft
  → Allow creating this skill? (y/n) y

Skill 'email-draft' created
```

Use it:

```bash
$ zhi -c "Use the email-draft skill: notify client Wang about the project acceptance being postponed to next Wednesday"
```

**Result:** A properly formatted business email draft ready to copy into your email client.

---

### 5.3 Data Analysis Skill

**Scenario:** Every month you need to produce a sales analysis report in a fixed format.

**Steps:**

```bash
$ zhi
You [approve]: Create a monthly data analysis skill that reads CSV data, \
...  calculates month-over-month growth, aggregates by dimension, \
...  and outputs both a Markdown report and an Excel summary
```

Use it:

```bash
$ zhi run monthly-report january-sales.csv
```

```
[file_read] Reading: january-sales.csv (25.6KB)
[file_write] Writing: monthly-report-2026-01.md (3.8KB)
[file_write] Writing: monthly-summary-2026-01.xlsx (5.2KB)

Files saved:
  zhi-output/monthly-report-2026-01.md
  zhi-output/monthly-summary-2026-01.xlsx
```

**Result:** A complete analysis report and Excel data table generated with a single command. Fixed format, consistent methodology, ready for management review.

---

## VI. Developer Workflows

### 6.1 Code Review with Custom Skill

**Scenario:** You want a quick automated review of source code before committing.

**Steps:**

Create a code review skill:

```yaml
name: code-review
description: Review source code and suggest improvements
model: glm-4-flash
system_prompt: |
  You are an experienced code reviewer. Read the provided source code and
  give actionable suggestions. Focus on:
  - Code quality and readability
  - Potential bugs or edge cases
  - Performance issues
  - Security concerns (injection, hardcoded secrets, etc.)
  Output as structured markdown with severity levels.
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
  description: Code review report
  directory: zhi-output
```

Run it:

```bash
$ zhi run code-review src/auth.py
```

**Result:** A structured review report with severity-tagged findings, ready to paste into a pull request comment.

### 6.2 Generate Test Data

**Scenario:** You need realistic test data for development or demos.

**Steps:**

```bash
$ zhi -c "Generate 50 rows of realistic test data for a user database: \
  name (Chinese), email, phone (Chinese format), registration date (2024-2026), \
  account status. Save as CSV."
```

```
[file_write] Writing: test-users.csv (4.2KB)

File saved: zhi-output/test-users.csv
```

**Result:** A CSV file with realistic, locale-appropriate test data. No real personal information is used.

### 6.3 Summarize Git History

**Scenario:** You need to write release notes or a changelog based on recent commits.

**Steps:**

```bash
$ git log --oneline --since="2026-02-01" | zhi -c "Organize these commits into a changelog grouped by category (features, fixes, chores)"
```

**Result:** A structured changelog with commits categorized and described in user-friendly language.

For a more detailed version:

```bash
$ git log --format="%h %s (%an, %ar)" --since="last month" | zhi -c "Write release notes for v2.5 based on these commits"
```

### 6.4 Cost-Effective Batch Processing

**Scenario:** You need to process a large number of files but want to keep costs down.

!!! info "Cost comparison"
    Skills use `glm-4-flash` by default, which costs approximately **10% of GLM-5** chat pricing. For batch operations, this difference adds up significantly.

**Strategy:** Use skills instead of interactive chat for repetitive tasks:

```bash
# Process 20 documents at ~10% of chat cost
for f in docs/*.md; do
  zhi run summarize "$f"
done

# Or use the daily-digest composite skill for a single combined report
zhi run daily-digest ./docs/
```

**Cost breakdown example:**

| Method | Model | Per-document cost | 20 documents |
|--------|-------|-------------------|--------------|
| Interactive chat | GLM-5 | ~0.05 CNY | ~1.00 CNY |
| Skill execution | GLM-4-flash | ~0.005 CNY | ~0.10 CNY |

Skills are the preferred approach for any repeatable, file-based workflow.

---

## Quick Reference

| Task | Command |
|------|---------|
| Start interactive mode | `zhi` |
| One-shot question | `zhi -c "your question"` |
| Pipe input | `cat file.txt \| zhi -c "summarize this"` |
| Run a skill | `zhi run <skill> [files...]` |
| First-time setup | `zhi --setup` |
| Check version | `zhi --version` |
| Debug mode | `zhi --debug` |

### Slash Commands in Interactive Mode

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/model glm-5` | Switch to GLM-5 (more capable, higher cost) |
| `/model glm-4-flash` | Switch to GLM-4-flash (faster, cheaper) |
| `/auto` | Auto mode (skip tool confirmation prompts) |
| `/approve` | Approve mode (default, confirm each tool call) |
| `/think` | Enable thinking mode (GLM-5 only) |
| `/fast` | Disable thinking mode |
| `/run <skill> [file]` | Run a skill from interactive mode |
| `/skill list` | List installed skills |
| `/skill new` | Create a new skill |
| `/reset` | Clear conversation history |
| `/undo` | Undo the last exchange |
| `/usage` | Show token usage for the current session |
| `/exit` | Exit zhi |

### Safety Reminders

- **All file writes** go to `zhi-output/` -- your original files are never modified.
- **Shell commands** always require manual confirmation, even in `/auto` mode.
- **Destructive commands** (`rm`, `mv`, etc.) trigger extra warnings.
- **Catastrophic commands** (`rm -rf /`, etc.) are permanently blocked.
- **OCR files** are limited to 20MB.
- **Skill names** only allow letters, digits, hyphens, and underscores.
