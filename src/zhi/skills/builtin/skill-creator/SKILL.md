---
name: skill-creator
description: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends the agent's capabilities with specialized knowledge, workflows, or tool integrations.
---

# Skill Creator

This skill provides guidance for creating effective skills in zhi.

## About Skills

Skills are modular packages that extend the agent's capabilities by providing specialized knowledge, workflows, and tools. They transform a general-purpose agent into a specialized one equipped with procedural knowledge for specific domains or tasks.

### What Skills Provide

1. Specialized workflows - Multi-step procedures for specific domains
2. Tool integrations - Instructions for working with specific file formats or APIs
3. Domain expertise - Company-specific knowledge, schemas, business logic
4. Bundled resources - Reference files for complex and repetitive tasks

## Core Principles

### Concise is Key

The context window is shared. Only add context the agent doesn't already have. Challenge each piece: "Does this justify its token cost?"

Prefer concise examples over verbose explanations.

### Set Appropriate Degrees of Freedom

**High freedom**: When multiple approaches are valid, decisions depend on context.
**Medium freedom**: When a preferred pattern exists, some variation is acceptable.
**Low freedom**: When operations are fragile, consistency is critical.

### Anatomy of a Skill

Every skill consists of a required SKILL.md file and optional reference files:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (required: name, description)
│   │   └── Optional: tools, version, model, max_turns, disable-model-invocation
│   └── Markdown instructions (required)
└── references/        - .md and .txt files auto-loaded into system prompt
    ├── guide.md
    └── examples.txt
```

**Important**: zhi only supports `references/` for bundled resources. Sibling `.md` and `.txt` files next to SKILL.md are also auto-loaded. Do NOT create `scripts/` or `assets/` directories — they are not supported.

#### SKILL.md (required)

- **Frontmatter** (YAML): `name` and `description` are required. Optional fields: `tools` (list of tool names), `version`, `model`, `max_turns`, `disable-model-invocation`.
- **Body** (Markdown): Instructions for executing the skill.

When `tools` is empty or omitted, the skill gets access to all base tools automatically.

#### Reference Files (optional)

Place `.md` and `.txt` files in `references/` or as siblings to SKILL.md. They are auto-loaded into the system prompt (up to 100KB total).

- Keep files focused on a single topic
- Use clear file names describing the content
- If total references exceed 100KB, they will be truncated

### Progressive Disclosure

Keep SKILL.md body under 500 lines. Split detailed content into reference files and describe when to consult them.

**Pattern 1: High-level guide with references**

```markdown
## Quick start
[core workflow]

## Advanced features
- **Form filling**: See references/forms.md
- **API reference**: See references/api.md
```

**Pattern 2: Domain-specific organization**

```
my-skill/
├── SKILL.md (overview and navigation)
└── references/
    ├── finance.md
    ├── sales.md
    └── product.md
```

## Skill Creation Process

1. Understand the skill with concrete examples
2. Plan reference content
3. Create the skill using `skill_create` tool
4. Iterate based on real usage

### Step 1: Understand the Skill

Ask the user:
- "What should this skill do? Can you give examples?"
- "What would a user say that should trigger this skill?"
- "Are there specific formats or constraints for the output?"

### Step 2: Plan Reference Content

For each example, identify what reference material would help:
- Domain schemas, API docs, company policies → `references/`
- Workflow guides, examples → `references/`

### Step 3: Create the Skill

Use the `skill_create` tool to create the skill. This is the primary creation mechanism in zhi.

#### `skill_create` Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `name` | Yes | Alphanumeric with hyphens/underscores (max 64 chars) |
| `description` | Yes | What the skill does and when to use it |
| `system_prompt` | Yes | Instructions (becomes SKILL.md body) |
| `tools` | Yes | List of tool names the skill can use |
| `format` | No | `skill_md` (default) or `yaml` (legacy) |
| `references` | No | File paths to copy into `references/` |
| `model` | No | Model to use (default: glm-4-flash) |
| `max_turns` | No | Max agent loop turns (default: 15) |
| `input_args` | No | Input argument definitions |
| `output` | No | Output configuration |
| `version` | No | Version string (e.g. "1.0.0") |
| `disable_model_invocation` | No | Return instructions directly without nested agent |

#### Available Base Tools

Skills can use these tools:
- **file_read**: Read file contents (text, PDF, images via OCR)
- **file_write**: Write files to the output directory
- **file_list**: List files and directories
- **web_fetch**: Fetch content from URLs
- **ask_user**: Ask the user questions during execution (always include for interactive skills)
- **ocr**: Extract text from images
- **shell**: Execute shell commands

**Tip**: Include `ask_user` whenever the skill may need to clarify ambiguous inputs.

#### Example: Creating a Report Skill

```
skill_create(
    name="weekly-report",
    description="Generate weekly project reports. Use when the user asks for a status report, weekly summary, or project update.",
    system_prompt="# Weekly Report Generator\n\nGenerate a structured weekly report...",
    tools=["file_read", "file_write", "ask_user"],
    references=["~/docs/report-template.md"]
)
```

#### Writing the `description`

The description is the primary trigger. Include:
- What the skill does
- Specific triggers/contexts for when to use it
- Example: "Comprehensive document creation and editing. Use when working with .docx files for: (1) Creating new documents, (2) Editing content, (3) Working with tracked changes"

#### Writing the `system_prompt`

This becomes the SKILL.md body. Use imperative form. Include:
- Core workflow steps
- Tool usage instructions
- Output format expectations
- References to bundled files (if any)

### Step 4: Iterate

1. Use the skill on real tasks
2. Notice struggles or inefficiencies
3. Update the skill contents
4. Test again

## Design Patterns

- **Multi-step processes**: See references/workflows.md for sequential and conditional workflow patterns
- **Output formats**: See references/output-patterns.md for template and example patterns
