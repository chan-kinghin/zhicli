# Comparison Heuristics

## File Type Handling

- **Text/Markdown**: Line-by-line diff, report sections that changed.
- **CSV/TSV**: Compare header rows first, then data rows. Report added/removed columns and row-level changes.
- **JSON/YAML**: Normalize key order, compare nested structures. Report path-based diffs (e.g., `$.config.timeout` changed from 30 to 60).
- **PDF/Images**: Use OCR to extract text, then compare extracted content. Note that formatting differences may appear as content changes.
- **Code files**: Treat as text but group changes by function/class where possible.

## Similarity Scoring

- **High**: Less than 10% of content differs (minor edits, typo fixes).
- **Medium**: 10-50% of content differs (section rewrites, structural changes).
- **Low**: More than 50% of content differs (near-complete rewrite or unrelated documents).

## Output Format Guidance

- Always produce a single markdown file as the comparison report.
- Use tables for columnar data comparisons.
- Use diff-style code blocks (```diff) for line-level changes when helpful.
- Keep the report concise: summarize repetitive patterns instead of listing every instance.
- When files are identical, state this clearly and skip the Differences section.
